"""AI-native meal plan, version, and conversation APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.plan import (
    PlanCreate,
    PlanCreateResponse,
    PlanMessageCreate,
    PlanMessageResponse,
    PlanResultResponse,
    PlanRunResponse,
    PlanStatusResponse,
    PlanRunningResponse,
    ProgressInfo,
    StepInfo,
)
from app.db.database import get_db
from app.models.meal_plan import MealPlan
from app.models.meal_plan_message import MealPlanMessage
from app.models.meal_plan_run import MealPlanRun
from app.models.meal_plan_version import MealPlanVersion
from app.models.profile import Profile
from app.models.user import User
from app.services.security import get_current_user
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
        status=plan.status,
        created_at=plan.created_at,
        links={
            "status": f"/api/v1/plans/{plan.plan_id}/status",
            "result": f"/api/v1/plans/{plan.plan_id}",
            "run": f"/api/v1/plans/{plan.plan_id}/runs/{run.run_id}",
        },
    )


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
    plan = _get_plan_or_404(db, plan_id, current_user)
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
    "generation_context": 3,
    "参考上下文": 3,
    "recommendation": 4,
    "recommendation_engine": 4,
    "plan_generation": 4,
    "AI 生成方案": 4,
    "validation": 5,
    "plan_validation": 5,
    "plan_repair": 5,
    "方案校验": 5,
    "aggregator": 6,
    "plan_aggregation": 6,
    "营养与预算汇总": 6,
    "summary": 7,
    "completed": 7,
    "保存方案版本": 7,
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
