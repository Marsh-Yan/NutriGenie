"""AI-native meal plan, version, and conversation APIs."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.schemas.plan import (
    PlanCreate,
    PlanCreateResponse,
    PlanListItem,
    PlanMessageCreate,
    PlanMessageResponse,
    PlanResultResponse,
    PlanRunResponse,
    PlanStatusResponse,
    PlanRunningResponse,
    ProgressInfo,
    StepInfo,
)
from app.api.schemas.v21 import ExecutionUpdate, MealReplaceRequest, PlanCloneRequest, PlanMetadataUpdate, PlanSummary
from app.db.database import get_db
from app.models.meal_plan import MealPlan
from app.models.meal_plan_message import MealPlanMessage
from app.models.meal_plan_run import MealPlanRun
from app.models.meal_plan_version import MealPlanVersion
from app.models.plan_execution_event import PlanExecutionArchive, PlanExecutionEvent
from app.models.profile import Profile
from app.models.user import User
from app.services.security import get_current_user
from app.services.meal_replacement import replace_meal_in_snapshot
from app.services.execution_binding import meal_keys, reconcile_execution
from app.tasks.plan_task import STEPS, enqueue_edit, enqueue_initial_plan, retry_latest_run

router = APIRouter(tags=["plans"])


def _can_access_plan(db: Session, plan: MealPlan, user: User) -> bool:
    if user.role == "admin":
        return True
    profile = db.get(Profile, plan.profile_id)
    return bool(profile and profile.user_id == user.user_id)


def _get_plan_or_404(db: Session, plan_id: int, user: User) -> MealPlan:
    plan = db.get(MealPlan, plan_id)
    if not plan or not _can_access_plan(db, plan, user):
        raise HTTPException(status_code=404, detail="规划任务不存在")
    return plan


def _latest_run(db: Session, plan_id: int) -> MealPlanRun | None:
    return db.query(MealPlanRun).filter(MealPlanRun.plan_id == plan_id).order_by(MealPlanRun.run_id.desc()).first()


@router.post("/plans", response_model=PlanCreateResponse, status_code=202)
def api_create_plan(
    data: PlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.profile_service import get_profile
    from app.workflow.nodes.intent_analyzer import explicit_duration_days

    requested_days = explicit_duration_days(data.user_input)
    if requested_days is not None and not 1 <= requested_days <= 7:
        raise HTTPException(status_code=422, detail="当前仅支持生成 1-7 天餐单")

    profile = get_profile(db, data.profile_id)
    if not profile or (current_user.role != "admin" and profile.user_id != current_user.user_id):
        raise HTTPException(status_code=400, detail="profile_id 不存在")

    plan = MealPlan(
        profile_id=data.profile_id,
        user_input=data.user_input,
        duration_days=data.duration_days,
        total_budget=data.total_budget,
        status="pending",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    run = enqueue_initial_plan(db, plan)

    return PlanCreateResponse(
        plan_id=plan.plan_id,
        status=run.status if run.status in ("pending", "running") else plan.status,
        created_at=plan.created_at,
        links={
            "status": f"/api/v1/plans/{plan.plan_id}/status",
            "result": f"/api/v1/plans/{plan.plan_id}",
            "run": f"/api/v1/plans/{plan.plan_id}/runs/{run.run_id}",
        },
    )


@router.get("/plans")
def api_list_plans(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    status: str | None = Query(None, pattern="^(pending|running|completed|failed)$"),
    archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Paginated V2.1 index; bare legacy requests retain the old array contract."""
    query = db.query(MealPlan).join(Profile, Profile.profile_id == MealPlan.profile_id)
    if current_user.role != "admin":
        query = query.filter(Profile.user_id == current_user.user_id)
    if not request.query_params:
        plans = query.order_by(MealPlan.created_at.desc(), MealPlan.plan_id.desc()).all()
        return [
            PlanListItem(
                plan_id=plan.plan_id,
                status=plan.status,
                user_input=plan.user_input,
                duration_days=plan.duration_days or 7,
                total_budget=float(plan.total_budget or 0),
                created_at=plan.created_at,
                completed_at=plan.completed_at,
            )
            for plan in plans
        ]
    query = query.filter(MealPlan.archived_at.is_not(None) if archived else MealPlan.archived_at.is_(None))
    if status:
        query = query.filter(MealPlan.status == status)
    total = query.count()
    plans = query.order_by(MealPlan.created_at.desc(), MealPlan.plan_id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [PlanSummary(
            plan_id=plan.plan_id,
            title=plan.title or f"{plan.duration_days or 7} 天饮食计划",
            status=plan.status,
            duration_days=plan.duration_days or 7,
            total_budget=float(plan.total_budget or 0),
            created_at=plan.created_at,
            completed_at=plan.completed_at,
            archived_at=plan.archived_at,
            source_plan_id=plan.source_plan_id,
        ).model_dump(mode="json") for plan in plans],
    }


@router.patch("/plans/{plan_id}", response_model=PlanSummary)
def api_update_plan_metadata(
    plan_id: int,
    data: PlanMetadataUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_plan_or_404(db, plan_id, current_user)
    if "title" in data.model_fields_set:
        plan.title = data.title.strip()
    if data.archived is not None:
        plan.archived_at = datetime.now(timezone.utc) if data.archived else None
    db.commit()
    db.refresh(plan)
    return PlanSummary(
        plan_id=plan.plan_id,
        title=plan.title or f"{plan.duration_days or 7} 天饮食计划",
        status=plan.status,
        duration_days=plan.duration_days or 7,
        total_budget=float(plan.total_budget or 0),
        created_at=plan.created_at,
        completed_at=plan.completed_at,
        archived_at=plan.archived_at,
        source_plan_id=plan.source_plan_id,
    )


@router.post("/plans/{plan_id}/clone", response_model=PlanCreateResponse, status_code=202)
def api_clone_plan(
    plan_id: int,
    data: PlanCloneRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = _get_plan_or_404(db, plan_id, current_user)
    clone = MealPlan(
        profile_id=source.profile_id,
        user_input=source.user_input,
        duration_days=source.duration_days,
        total_budget=data.overrides.total_budget if data.overrides.total_budget is not None else source.total_budget,
        title=data.title.strip() if data.title else source.title,
        source_plan_id=source.plan_id,
        status="pending",
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    run = enqueue_initial_plan(db, clone)
    return PlanCreateResponse(
        plan_id=clone.plan_id,
        status=run.status if run.status in ("pending", "running") else clone.status,
        created_at=clone.created_at,
        links={
            "status": f"/api/v1/plans/{clone.plan_id}/status",
            "result": f"/api/v1/plans/{clone.plan_id}",
            "run": f"/api/v1/plans/{clone.plan_id}/runs/{run.run_id}",
        },
    )


def _execution_payload(db: Session, plan: MealPlan) -> dict:
    current_keys = meal_keys(plan.result_json)
    events = db.query(PlanExecutionEvent).filter(PlanExecutionEvent.plan_id == plan.plan_id).order_by(
        PlanExecutionEvent.day, PlanExecutionEvent.meal_slot,
    ).all()
    return {"plan_id": plan.plan_id, "events": [{
        "day": event.day,
        "meal_slot": event.meal_slot,
        "status": event.status,
        "note": event.note,
        "recipe_key": event.recipe_key or current_keys.get((event.day, event.meal_slot)),
        "version_id": event.version_id,
        "updated_at": event.updated_at,
    } for event in events if current_keys.get((event.day, event.meal_slot)) == (event.recipe_key or current_keys.get((event.day, event.meal_slot)))]}


@router.get("/plans/{plan_id}/execution/history")
def api_get_execution_history(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_plan_or_404(db, plan_id, current_user)
    archived = db.query(PlanExecutionArchive).filter(
        PlanExecutionArchive.plan_id == plan.plan_id,
    ).order_by(PlanExecutionArchive.archive_id.desc()).all()
    return {"plan_id": plan_id, "events": [{
        "day": event.day, "meal_slot": event.meal_slot,
        "status": event.status, "note": event.note,
        "recipe_key": event.recipe_key, "version_id": event.version_id,
        "archived_at": event.archived_at,
    } for event in archived]}


@router.get("/plans/{plan_id}/execution")
def api_get_execution(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_plan_or_404(db, plan_id, current_user)
    return _execution_payload(db, plan)


@router.put("/plans/{plan_id}/execution")
def api_put_execution(
    plan_id: int,
    data: ExecutionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_plan_or_404(db, plan_id, current_user)
    if plan.status != "completed" or not plan.result_json:
        raise HTTPException(status_code=409, detail="方案尚未完成，不能记录执行状态")
    available = {(int(day.get("day", 0)), slot) for day in plan.result_json.get("weekly_plan", []) for slot in (day.get("meals") or {})}
    for event in data.events:
        if (event.day, event.meal_slot) not in available:
            raise HTTPException(status_code=422, detail=f"第 {event.day} 天 {event.meal_slot} 不在当前方案中")
    owner = db.get(Profile, plan.profile_id).user_id
    current_keys = meal_keys(plan.result_json)
    reconcile_execution(db, plan_id=plan_id, old_result=plan.result_json,
                        old_version_id=plan.current_version_id, new_result=plan.result_json)
    for event in data.events:
        existing = db.query(PlanExecutionEvent).filter(
            PlanExecutionEvent.plan_id == plan_id,
            PlanExecutionEvent.day == event.day,
            PlanExecutionEvent.meal_slot == event.meal_slot,
        ).with_for_update().first()
        if existing:
            existing.status = event.status
            existing.note = event.note
            existing.recipe_key = current_keys[(event.day, event.meal_slot)]
            existing.version_id = plan.current_version_id
        else:
            db.add(PlanExecutionEvent(
                plan_id=plan_id, user_id=owner, day=event.day,
                meal_slot=event.meal_slot, status=event.status, note=event.note,
                recipe_key=current_keys[(event.day, event.meal_slot)], version_id=plan.current_version_id,
            ))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="餐次状态已被并发更新，请重新读取后重试") from exc
    return _execution_payload(db, plan)


@router.post("/plans/{plan_id}/execution/import")
def api_import_execution(
    plan_id: int,
    data: ExecutionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import legacy local events without replacing any server-owned slot."""
    plan = _get_plan_or_404(db, plan_id, current_user)
    if plan.status != "completed" or not plan.result_json:
        raise HTTPException(status_code=409, detail="方案尚未完成，不能导入执行状态")
    available = {(int(day.get("day", 0)), slot) for day in plan.result_json.get("weekly_plan", []) for slot in (day.get("meals") or {})}
    for event in data.events:
        if (event.day, event.meal_slot) not in available:
            raise HTTPException(status_code=422, detail=f"第 {event.day} 天 {event.meal_slot} 不在当前方案中")
    existing = {
        (row.day, row.meal_slot) for row in db.query(PlanExecutionEvent).filter(
            PlanExecutionEvent.plan_id == plan_id,
        ).with_for_update().all()
    }
    owner = db.get(Profile, plan.profile_id).user_id
    current_keys = meal_keys(plan.result_json)
    for event in data.events:
        if (event.day, event.meal_slot) not in existing:
            db.add(PlanExecutionEvent(
                plan_id=plan_id, user_id=owner, day=event.day,
                meal_slot=event.meal_slot, status=event.status, note=event.note,
                recipe_key=current_keys[(event.day, event.meal_slot)], version_id=plan.current_version_id,
            ))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="服务端餐次已变化，请重新同步后再导入") from exc
    return _execution_payload(db, plan)


@router.post("/plans/{plan_id}/meals/{day}/{meal_slot}/replace")
def api_replace_meal(
    plan_id: int,
    day: int,
    meal_slot: str,
    data: MealReplaceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = db.query(MealPlan).filter(MealPlan.plan_id == plan_id).with_for_update().first()
    if not plan or not _can_access_plan(db, plan, current_user):
        raise HTTPException(status_code=404, detail="规划任务不存在")
    if day < 1 or day > (plan.duration_days or 7) or meal_slot not in ("breakfast", "lunch", "dinner"):
        raise HTTPException(status_code=422, detail="无效的日期或餐次")
    if plan.status != "completed" or not plan.current_version_id or not plan.result_json:
        raise HTTPException(status_code=409, detail="方案尚未完成，不能替换餐食")
    if db.query(MealPlanRun).filter(MealPlanRun.plan_id == plan_id, MealPlanRun.status.in_(("pending", "running"))).first():
        raise HTTPException(status_code=409, detail="当前方案正在生成，暂不能替换餐食")
    executed = db.query(PlanExecutionEvent).filter(
        PlanExecutionEvent.plan_id == plan_id,
        PlanExecutionEvent.day == day,
        PlanExecutionEvent.meal_slot == meal_slot,
        PlanExecutionEvent.status == "completed",
    ).first()
    if executed:
        raise HTTPException(status_code=409, detail="该餐已标记完成，不能把旧执行记录当作新菜谱")
    profile = db.get(Profile, plan.profile_id)
    result = replace_meal_in_snapshot(
        plan.result_json, day=day, slot=meal_slot, reason=data.reason,
        excluded_ids=data.exclude_recipe_ids, excluded_keys=data.exclude_recipe_keys,
        duration_days=plan.duration_days or 7,
        profile_allergies=profile.allergies or [], profile_diet_type=profile.diet_type,
        total_budget=float(plan.total_budget or 0),
    )
    if not result:
        raise HTTPException(status_code=409, detail="当前没有满足过敏原、营养、预算和多样性约束的替代菜谱")
    latest = db.query(MealPlanVersion).filter(MealPlanVersion.plan_id == plan_id).order_by(MealPlanVersion.version_no.desc()).first()
    version = MealPlanVersion(
        plan_id=plan_id,
        version_no=(latest.version_no if latest else 0) + 1,
        parent_version_id=plan.current_version_id,
        result_json=result,
        validation_json=result.get("validation"),
        model_name="deterministic_replacement",
        prompt_version=None,
        rag_meta=result.get("generation_meta"),
    )
    db.add(version)
    db.flush()
    result = {**result, "version_id": version.version_id, "version_no": version.version_no}
    version.result_json = result
    reconcile_execution(db, plan_id=plan_id, old_result=plan.result_json,
                        old_version_id=plan.current_version_id, new_result=result)
    plan.result_json = result
    plan.current_version_id = version.version_id
    db.commit()
    day_result = next(item for item in result["weekly_plan"] if item["day"] == day)
    return {
        "plan_id": plan_id,
        "version_id": version.version_id,
        "meal": day_result["meals"][meal_slot],
        "daily_nutrition": day_result["total_nutrition"],
        "total_budget": float(plan.total_budget or 0),
        "estimated_total_cost": result["shopping_list"]["total_cost"],
        "plan_validation": result["validation"],
    }


@router.get("/plans/{plan_id}/status", response_model=PlanStatusResponse)
def api_get_plan_status(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_plan_or_404(db, plan_id, current_user)
    run = _latest_run(db, plan_id)
    current_node = run.current_node if run and run.status in ("pending", "running") else plan.current_node
    run_status = run.status if run else plan.status
    has_current = bool(plan.current_version_id)
    response = PlanStatusResponse(
        plan_id=plan.plan_id,
        status=plan.status,
        run_id=run.run_id if run else None,
        run_status=run_status,
        current_node=current_node,
        current_version_id=plan.current_version_id,
        has_current_version=has_current,
        created_at=plan.created_at,
        completed_at=plan.completed_at,
        last_error=run.error_message if run and run.status == "failed" else None,
    )

    if run and run.status in ("pending", "running"):
        order = _find_step_order(current_node or "")
        steps = []
        completed = 0
        current_step = 0
        for step in STEPS:
            if step["order"] < order:
                status = "completed"
                completed += 1
            elif step["order"] == order:
                status = "running"
                current_step = step["order"]
            else:
                status = "pending"
            steps.append(StepInfo(name=step["name"], status=status, order=step["order"]))
        response.progress = ProgressInfo(
            total_steps=len(STEPS),
            completed_steps=completed,
            current_step=current_step or 1,
            step_name=_node_to_step_name(current_node or ""),
            steps=steps,
        )
    if plan.status == "failed" and not has_current:
        response.error = plan.error_message
    return response


@router.get("/plans/{plan_id}")
def api_get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_plan_or_404(db, plan_id, current_user)
    if plan.status in ("pending", "running") and not plan.result_json:
        return PlanRunningResponse(
            plan_id=plan.plan_id,
            status=plan.status,
            current_node=plan.current_node,
            current_version_id=plan.current_version_id,
            has_current_version=bool(plan.current_version_id),
        )
    return {
        "plan_id": plan.plan_id,
        "status": plan.status,
        "profile_id": plan.profile_id,
        "title": plan.title,
        "source_plan_id": plan.source_plan_id,
        "archived_at": plan.archived_at,
        "user_input": plan.user_input,
        "created_at": plan.created_at,
        "completed_at": plan.completed_at,
        "current_version_id": plan.current_version_id,
        "result": plan.result_json,
        "last_error": plan.error_message if plan.current_version_id else None,
    }


@router.post("/plans/{plan_id}/messages", response_model=PlanRunResponse, status_code=202)
def api_create_plan_message(
    plan_id: int,
    data: PlanMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_plan_or_404(db, plan_id, current_user)
    message = data.message.strip()
    if not message and data.action:
        message = _action_to_message(data.action)
    if not message:
        raise HTTPException(status_code=422, detail="请提供修改内容或快捷操作")
    try:
        _, run = enqueue_edit(
            db,
            plan,
            message=message,
            action=data.action,
            client_request_id=data.client_request_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PlanRunResponse(
        run_id=run.run_id,
        plan_id=plan_id,
        status=run.status,
        base_version_id=run.base_version_id,
    )


@router.post("/plans/{plan_id}/retry", response_model=PlanRunResponse, status_code=202)
def api_retry_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_plan_or_404(db, plan_id, current_user)
    try:
        run = retry_latest_run(db, plan)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PlanRunResponse(
        run_id=run.run_id,
        plan_id=plan_id,
        status=run.status,
        base_version_id=run.base_version_id,
    )


@router.get("/plans/{plan_id}/messages", response_model=list[PlanMessageResponse])
def api_list_plan_messages(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_plan_or_404(db, plan_id, current_user)
    messages = db.query(MealPlanMessage).filter(MealPlanMessage.plan_id == plan.plan_id).order_by(MealPlanMessage.message_id.asc()).all()
    return [
        PlanMessageResponse(
            message_id=item.message_id,
            plan_id=item.plan_id,
            version_id=item.version_id,
            role=item.role,
            content=item.content,
            action=item.action_json,
            status=item.status,
            created_at=item.created_at,
        )
        for item in messages
    ]


@router.get("/plans/{plan_id}/versions")
def api_list_plan_versions(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_plan_or_404(db, plan_id, current_user)
    versions = db.query(MealPlanVersion).filter(MealPlanVersion.plan_id == plan.plan_id).order_by(MealPlanVersion.version_no.desc()).all()
    return {
        "plan_id": plan_id,
        "current_version_id": plan.current_version_id,
        "items": [
            {
                "version_id": item.version_id,
                "version_no": item.version_no,
                "parent_version_id": item.parent_version_id,
                "validation": item.validation_json,
                "created_at": item.created_at,
                "is_current": item.version_id == plan.current_version_id,
            }
            for item in versions
        ],
    }


@router.get("/plans/{plan_id}/versions/{version_id}")
def api_get_plan_version(
    plan_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_plan_or_404(db, plan_id, current_user)
    version = db.query(MealPlanVersion).filter(MealPlanVersion.plan_id == plan.plan_id, MealPlanVersion.version_id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="方案版本不存在")
    return {
        "plan_id": plan_id,
        "version_id": version.version_id,
        "version_no": version.version_no,
        "parent_version_id": version.parent_version_id,
        "created_at": version.created_at,
        "result": version.result_json,
    }


@router.post("/plans/{plan_id}/versions/{version_id}/restore")
def api_restore_plan_version(
    plan_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = db.query(MealPlan).filter(MealPlan.plan_id == plan_id).with_for_update().first()
    if not plan or not _can_access_plan(db, plan, current_user):
        raise HTTPException(status_code=404, detail="规划任务不存在")
    if db.query(MealPlanRun).filter(
        MealPlanRun.plan_id == plan_id,
        MealPlanRun.status.in_(("pending", "running")),
    ).first():
        raise HTTPException(status_code=409, detail="当前方案正在生成，暂不能恢复历史版本")
    source = db.query(MealPlanVersion).filter(MealPlanVersion.plan_id == plan.plan_id, MealPlanVersion.version_id == version_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="方案版本不存在")
    latest = db.query(MealPlanVersion).filter(MealPlanVersion.plan_id == plan.plan_id).order_by(MealPlanVersion.version_no.desc()).first()
    version = MealPlanVersion(
        plan_id=plan.plan_id,
        version_no=(latest.version_no if latest else 0) + 1,
        parent_version_id=source.version_id,
        result_json=dict(source.result_json),
        validation_json=source.validation_json,
        model_name=source.model_name,
        prompt_version=source.prompt_version,
        rag_meta=source.rag_meta,
    )
    db.add(version)
    db.flush()
    result = dict(version.result_json)
    result["version_id"] = version.version_id
    result["version_no"] = version.version_no
    version.result_json = result
    reconcile_execution(db, plan_id=plan_id, old_result=plan.result_json,
                        old_version_id=plan.current_version_id, new_result=result)
    plan.current_version_id = version.version_id
    plan.result_json = result
    plan.status = "completed"
    plan.error_message = None
    plan.completed_at = plan.completed_at
    db.add(MealPlanMessage(
        plan_id=plan.plan_id,
        version_id=version.version_id,
        role="assistant",
        content=f"已恢复方案版本 {source.version_no}。",
        status="completed",
    ))
    db.commit()
    return {"plan_id": plan_id, "version_id": version.version_id, "version_no": version.version_no, "result": result}


@router.get("/plans/{plan_id}/runs/{run_id}", response_model=PlanRunResponse)
def api_get_plan_run(
    plan_id: int,
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_plan_or_404(db, plan_id, current_user)
    run = db.query(MealPlanRun).filter(MealPlanRun.plan_id == plan.plan_id, MealPlanRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="生成任务不存在")
    return PlanRunResponse(
        run_id=run.run_id,
        plan_id=run.plan_id,
        status=run.status,
        current_node=run.current_node,
        base_version_id=run.base_version_id,
        output_version_id=run.output_version_id,
        error=run.error_message,
    )


NODE_STEP_MAP = {
    "intent_analyzer": 1,
    "意图分析": 1,
    "constraint": 2,
    "constraint_analyzer": 2,
    "约束分析": 2,
    "约束构建": 2,
    "generation_context": 3,
    "参考上下文": 3,
    "食材知识": 3,
    "recommendation": 4,
    "recommendation_engine": 4,
    "plan_generation": 4,
    "AI 生成方案": 4,
    "AI 创作候选": 4,
    "recipe_normalization": 5,
    "食材标准化": 5,
    "candidate_validation": 6,
    "plan_repair": 6,
    "硬约束校验": 6,
    "weekly_optimizer": 7,
    "整周优化": 7,
    "validation": 8,
    "plan_validation": 8,
    "aggregator": 8,
    "plan_aggregation": 8,
    "结果校验与汇总": 8,
    "summary": 9,
    "completed": 9,
    "保存方案版本": 9,
}


def _find_step_order(node_name: str) -> int:
    return NODE_STEP_MAP.get(node_name or "", 0)


def _node_to_step_name(node_name: str) -> str:
    order = _find_step_order(node_name)
    return STEPS[order - 1]["name"] if 1 <= order <= len(STEPS) else node_name


def _action_to_message(action: dict) -> str:
    action_type = action.get("type")
    day = action.get("day")
    slot = action.get("slot")
    labels = {
        "replace_meal": f"重新生成第{day}天{slot or '指定餐次'}",
        "replace_day": f"重新生成第{day}天的全部餐食",
        "reduce_budget": "降低总预算，保持营养结构尽量稳定",
        "increase_protein": "提高每日蛋白质，保持总热量合理",
        "remove_ingredient": f"去除食材：{action.get('ingredient', '')}",
        "shorter_cooking": "缩短烹饪时间，优先选择简单做法",
    }
    return labels.get(action_type, "按照快捷操作重新优化当前方案")
