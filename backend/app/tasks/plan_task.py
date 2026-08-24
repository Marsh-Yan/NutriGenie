"""规划任务管理器（In-Memory 版本）

Phase 2: Mock 数据模拟。
Phase 4: 真实 LangGraph Workflow 调用（替换 _generate_mock_result）。
"""

import asyncio
import logging
import threading
from datetime import datetime, timezone

from app.db.database import SessionLocal
from app.models.meal_plan import MealPlan
from app.workflow.graph import compiled_graph
from app.workflow.state import WorkflowState

logger = logging.getLogger(__name__)

# ─── 规划执行步骤（用于前端进度显示）─────────────

STEPS = [
    {"name": "意图分析", "order": 1},
    {"name": "约束分析", "order": 2},
    {"name": "混合推荐", "order": 3},
    {"name": "计划聚合", "order": 4},
    {"name": "结果校验", "order": 5},
    {"name": "生成总结", "order": 6},
]


def _resolve_node_step(node_name: str) -> int:
    """将节点名映射到步骤序号"""
    mapping = {
        "intent_analyzer": 1,
        "constraint_analyzer": 2,
        "constraint": 2,
        "recommendation_engine": 3,
        "recommendation": 3,
        "aggregator": 4,
        "plan_validation": 5,
        "validation": 5,
        "summary_generator": 6,
        "summary": 6,
    }
    return mapping.get(node_name, 0)


def _node_to_step_name(node_name: str) -> str:
    """将节点名转为前端显示名称"""
    mapping = {
        "intent_analyzer": "意图分析",
        "constraint_analyzer": "约束分析",
        "constraint": "约束分析",
        "recommendation_engine": "混合推荐",
        "recommendation": "混合推荐",
        "aggregator": "计划聚合",
        "plan_validation": "结果校验",
        "validation": "结果校验",
        "summary_generator": "生成总结",
        "summary": "生成总结",
        "completed": "生成总结",
    }
    return mapping.get(node_name, node_name)


def _state_value(state, key: str, default=None):
    """Read a LangGraph state value from either dict or dataclass output."""
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


async def _run_workflow_with_progress(state: WorkflowState, plan: MealPlan, db):
    """Run the graph while persisting each user-visible node transition."""
    final_state = None
    last_node = None
    async for snapshot in compiled_graph.astream(state, stream_mode="values"):
        final_state = snapshot
        current_node = _state_value(snapshot, "current_node")
        if current_node and current_node not in (last_node, "completed"):
            last_node = current_node
            plan.current_node = current_node
            db.commit()
    return final_state or {}


def _execute_plan(plan_id: int):
    """在线程中执行规划任务

    使用 LangGraph Workflow 生成真实推荐结果。
    逐步更新状态以支持前端轮询进度。
    """
    db = SessionLocal()
    try:
        plan = db.query(MealPlan).filter(MealPlan.plan_id == plan_id).first()
        if not plan:
            logger.error(f"Plan {plan_id} not found")
            return

        # ── 初始化 Workflow ──
        state = WorkflowState(
            profile_id=plan.profile_id,
            user_input=plan.user_input or "",
            duration_days=plan.duration_days or 7,
            total_budget=float(plan.total_budget or 0),
        )

        # ── 更新为 running ──
        plan.status = "running"
        plan.current_node = "intent_analyzer"
        db.commit()

        # ── 异步执行 Workflow ──
        final_state = asyncio.run(_run_workflow_with_progress(state, plan, db))

        # ── 检查结果 ──
        final_result = _state_value(final_state, "final_result", {}) or {}
        status = final_result.get("status", "failed")

        if status == "completed":
            aggregated = _state_value(final_state, "aggregated_result", {}) or {}

            # 提取前端需要的字段
            result_json = {
                "top5": aggregated.get("top5", []),
                "weekly_plan": aggregated.get("weekly_plan", []),
                "nutrition_report": aggregated.get("nutrition_report", {}),
                "shopping_list": aggregated.get("shopping_list", {}),
                "recommendation_meta": aggregated.get("recommendation_meta", {}),
                "plan_validation": aggregated.get("plan_validation", {}),
                "summary": _state_value(final_state, "summary", "")
                            or aggregated.get("summary", "饮食规划已生成。"),
            }

            plan.status = "completed"
            plan.current_node = None
            plan.result_json = result_json
            plan.completed_at = datetime.now(timezone.utc)
            logger.info(f"Plan {plan_id} completed via Workflow")
        else:
            errors = _state_value(final_state, "errors", [])
            error_msg = errors[-1] if errors else "规划生成失败"
            plan.status = "failed"
            plan.current_node = None
            plan.error_message = error_msg
            logger.error(f"Plan {plan_id} failed: {error_msg}")

        db.commit()

    except Exception as e:
        logger.exception(f"Plan {plan_id} execution error")
        try:
            plan = db.query(MealPlan).filter(MealPlan.plan_id == plan_id).first()
            if plan:
                plan.status = "failed"
                plan.current_node = None
                plan.error_message = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def start_plan_task(plan_id: int) -> None:
    """启动规划后台线程"""
    thread = threading.Thread(target=_execute_plan, args=(plan_id,), daemon=True)
    thread.start()
