"""Background execution for initial AI plans and conversational edits."""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import SessionLocal
from app.models.meal_plan import MealPlan
from app.models.meal_plan_message import MealPlanMessage
from app.models.meal_plan_run import MealPlanRun
from app.models.meal_plan_version import MealPlanVersion
from app.workflow.graph import compiled_graph
from app.workflow.state import WorkflowState

logger = logging.getLogger(__name__)

STEPS = [
    {"name": "意图分析", "order": 1},
    {"name": "约束分析", "order": 2},
    {"name": "参考上下文", "order": 3},
    {"name": "AI 生成方案", "order": 4},
    {"name": "方案校验", "order": 5},
    {"name": "营养与预算汇总", "order": 6},
    {"name": "保存方案版本", "order": 7},
]

HARD_CONSTRAINT_MARKERS = (
    "预算",
    "过敏",
    "忌口",
    "不吃",
    "不能吃",
    "饮食类型",
    "素食",
    "纯素",
    "无麸质",
    "生酮",
    "高蛋白",
    "减脂",
    "减肥",
    "增肌",
    "控糖",
    "血糖",
    "健康目标",
    "规划天数",
    "天餐单",
)


def _edit_changes_hard_constraints(message: str) -> bool:
    """Whether an edit explicitly asks to change intent-level constraints."""
    normalized = (message or "").strip().lower()
    return any(marker in normalized for marker in HARD_CONSTRAINT_MARKERS)


def _resolve_node_step(node_name: str) -> int:
    mapping = {
        "intent_analyzer": 1,
        "constraint_analyzer": 2,
        "constraint": 2,
        "generation_context": 3,
        "plan_generation": 4,
        "recommendation_engine": 4,
        "recommendation": 4,
        "plan_validation": 5,
        "plan_repair": 5,
        "validation": 5,
        "plan_aggregation": 6,
        "aggregator": 6,
        "summary": 7,
        "completed": 7,
    }
    return mapping.get(node_name, 0)


def _node_to_step_name(node_name: str) -> str:
    mapping = {item["name"]: item["name"] for item in STEPS}
    mapping.update({
        "intent_analyzer": "意图分析",
        "constraint_analyzer": "约束分析",
        "constraint": "约束分析",
        "generation_context": "参考上下文",
        "plan_generation": "AI 生成方案",
        "recommendation": "AI 生成方案",
        "plan_validation": "方案校验",
        "plan_repair": "方案校验",
        "plan_aggregation": "营养与预算汇总",
        "aggregator": "营养与预算汇总",
        "summary": "保存方案版本",
        "completed": "保存方案版本",
    })
    return mapping.get(node_name, node_name)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _running_run(db: Session, plan_id: int) -> MealPlanRun | None:
    return (
        db.query(MealPlanRun)
        .filter(MealPlanRun.plan_id == plan_id, MealPlanRun.status.in_(["pending", "running"]))
        .order_by(MealPlanRun.run_id.desc())
        .first()
    )


def enqueue_initial_plan(db: Session, plan: MealPlan) -> MealPlanRun:
    user_message = MealPlanMessage(
        plan_id=plan.plan_id,
        role="user",
        content=plan.user_input,
        status="accepted",
    )
    db.add(user_message)
    db.flush()
    run = MealPlanRun(
        plan_id=plan.plan_id,
        trigger_message_id=user_message.message_id,
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    start_generation_run(run.run_id)
    return run


def enqueue_edit(
    db: Session,
    plan: MealPlan,
    *,
    message: str,
    action: dict | None = None,
    client_request_id: str | None = None,
) -> tuple[MealPlanMessage, MealPlanRun]:
    # Serialize edits per plan where the database supports row locks.  This
    # closes the check-then-insert race between two simultaneous edit calls.
    locked_plan = (
        db.query(MealPlan)
        .filter(MealPlan.plan_id == plan.plan_id)
        .with_for_update()
        .first()
    )
    if locked_plan:
        plan = locked_plan

    if client_request_id:
        existing = (
            db.query(MealPlanRun)
            .filter(
                MealPlanRun.plan_id == plan.plan_id,
                MealPlanRun.client_request_id == client_request_id,
            )
            .order_by(MealPlanRun.run_id.desc())
            .first()
        )
        if existing:
            existing_message = db.get(MealPlanMessage, existing.trigger_message_id)
            return existing_message, existing

    if _running_run(db, plan.plan_id):
        raise ValueError("当前方案已有生成任务正在运行")

    if not plan.current_version_id:
        raise ValueError("方案尚未生成完成，暂不能编辑")

    user_message = MealPlanMessage(
        plan_id=plan.plan_id,
        version_id=plan.current_version_id,
        role="user",
        content=message,
        action_json=action,
        status="accepted",
    )
    db.add(user_message)
    db.flush()
    run = MealPlanRun(
        plan_id=plan.plan_id,
        base_version_id=plan.current_version_id,
        trigger_message_id=user_message.message_id,
        client_request_id=client_request_id,
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    start_generation_run(run.run_id)
    return user_message, run


def retry_latest_run(db: Session, plan: MealPlan) -> MealPlanRun:
    """Retry the latest failed generation without falling back to DB recipes."""
    if _running_run(db, plan.plan_id):
        raise ValueError("当前方案已有生成任务正在运行")

    latest = (
        db.query(MealPlanRun)
        .filter(MealPlanRun.plan_id == plan.plan_id)
        .order_by(MealPlanRun.run_id.desc())
        .first()
    )
    if not latest or latest.status != "failed":
        raise ValueError("当前没有可重试的失败任务")

    if plan.current_version_id:
        message = db.get(MealPlanMessage, latest.trigger_message_id) if latest.trigger_message_id else None
        if not message:
            raise ValueError("找不到上一次修改指令")
        _, run = enqueue_edit(
            db,
            plan,
            message=message.content,
            action=message.action_json,
        )
        return run

    run = enqueue_initial_plan(db, plan)
    return run


def start_plan_task(plan_id: int) -> None:
    """Create and start an initial generation run."""
    db = SessionLocal()
    try:
        plan = db.get(MealPlan, plan_id)
        if not plan:
            logger.error("Plan %s not found", plan_id)
            return
        enqueue_initial_plan(db, plan)
    finally:
        db.close()


def start_generation_run(run_id: int) -> None:
    thread = threading.Thread(target=_execute_run, args=(run_id,), daemon=True)
    thread.start()


def _build_state(db: Session, run: MealPlanRun, plan: MealPlan) -> WorkflowState:
    base_version = db.get(MealPlanVersion, run.base_version_id) if run.base_version_id else None
    message = db.get(MealPlanMessage, run.trigger_message_id) if run.trigger_message_id else None
    edit_message = message.content if base_version and message else None
    generation_meta = (base_version.result_json or {}).get("generation_meta", {}) if base_version else {}
    reuse_constraints = bool(base_version and edit_message and not _edit_changes_hard_constraints(edit_message))
    snapshot_constraints = generation_meta.get("constraints_snapshot") if reuse_constraints else None
    snapshot_intent = generation_meta.get("intent_snapshot") if reuse_constraints else None
    user_input = plan.user_input or ""
    if base_version and edit_message and not reuse_constraints:
        user_input = f"{user_input}\n本次明确修改要求：{edit_message}"
    return WorkflowState(
        profile_id=plan.profile_id,
        user_input=user_input,
        duration_days=plan.duration_days or 7,
        total_budget=float(plan.total_budget or 0),
        is_edit=bool(base_version),
        skip_intent=reuse_constraints,
        intent_analysis=snapshot_intent,
        constraints=snapshot_constraints,
        base_version_id=run.base_version_id,
        base_plan=base_version.result_json if base_version else None,
        edit_message=edit_message,
        edit_action=message.action_json if base_version and message else None,
    )


def _save_success(
    db: Session,
    run: MealPlanRun,
    plan: MealPlan,
    final_state: dict,
) -> None:
    result = dict(final_state.get("aggregated_result") or {})
    if not result:
        raise RuntimeError("工作流未返回可保存的 AI 方案")

    previous = (
        db.query(MealPlanVersion)
        .filter(MealPlanVersion.plan_id == plan.plan_id)
        .order_by(MealPlanVersion.version_no.desc())
        .first()
    )
    version_no = (previous.version_no if previous else 0) + 1
    version = MealPlanVersion(
        plan_id=plan.plan_id,
        version_no=version_no,
        parent_version_id=run.base_version_id,
        trigger_message_id=run.trigger_message_id,
        result_json=result,
        validation_json=result.get("validation", {}),
        model_name=settings.PLAN_GENERATION_MODEL or settings.LLM_MODEL,
        prompt_version=settings.PLAN_PROMPT_VERSION,
        rag_meta=result.get("generation_meta", {}),
    )
    db.add(version)
    db.flush()
    result["version_id"] = version.version_id
    result["version_no"] = version_no
    version.result_json = result

    plan.current_version_id = version.version_id
    plan.result_json = result
    plan.status = "completed"
    plan.current_node = None
    plan.error_message = None
    plan.completed_at = _now()

    run.status = "completed"
    run.output_version_id = version.version_id
    run.repair_attempts = int(final_state.get("repair_attempts") or 0)
    run.current_node = "completed"
    run.completed_at = _now()

    user_message = db.get(MealPlanMessage, run.trigger_message_id) if run.trigger_message_id else None
    if user_message:
        user_message.version_id = version.version_id
        user_message.status = "completed"
        db.add(MealPlanMessage(
            plan_id=plan.plan_id,
            version_id=version.version_id,
            role="assistant",
            content=result.get("summary", "AI 方案已生成。"),
            status="completed",
        ))


def _save_failure(db: Session, run: MealPlanRun, plan: MealPlan, error: str) -> None:
    run.status = "failed"
    run.current_node = None
    run.error_message = error[:2000]
    run.completed_at = _now()
    user_message = db.get(MealPlanMessage, run.trigger_message_id) if run.trigger_message_id else None
    if user_message:
        user_message.status = "failed"

    if plan.current_version_id:
        # The prior successful version remains the usable current result.
        plan.status = "completed"
        plan.current_node = None
        plan.error_message = error[:2000]
    else:
        plan.status = "failed"
        plan.current_node = None
        plan.error_message = error[:2000]


def _execute_run(run_id: int) -> None:
    db = SessionLocal()
    try:
        run = db.get(MealPlanRun, run_id)
        if not run:
            logger.error("Generation run %s not found", run_id)
            return
        plan = db.get(MealPlan, run.plan_id)
        if not plan:
            logger.error("Plan %s not found for run %s", run.plan_id, run_id)
            return

        run.status = "running"
        run.current_node = "intent_analyzer" if not run.base_version_id else "constraint"
        plan.status = "running"
        plan.current_node = run.current_node
        db.commit()

        state = _build_state(db, run, plan)
        final_state = asyncio.run(compiled_graph.ainvoke(state))
        final_result = final_state.get("final_result", {})
        if final_result.get("status") == "completed":
            _save_success(db, run, plan, final_state)
            logger.info("Plan %s run %s completed", plan.plan_id, run_id)
        else:
            errors = final_state.get("errors", [])
            error = errors[-1] if errors else final_result.get("error", "规划生成失败")
            _save_failure(db, run, plan, error)
            logger.warning("Plan %s run %s failed: %s", plan.plan_id, run_id, error)
        db.commit()
    except Exception as exc:
        logger.exception("Generation run %s failed unexpectedly", run_id)
        try:
            run = db.get(MealPlanRun, run_id)
            if run:
                plan = db.get(MealPlan, run.plan_id)
                if plan:
                    _save_failure(db, run, plan, str(exc))
                    db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()
