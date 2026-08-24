import asyncio

from app.api.routes.plans import _find_step_order, _node_to_step_name
from app.config import settings
from app.services.ai_plan_models import GeneratedPlan
from app.services.ingredient_catalog import load_seed_catalog
from app.tasks.plan_task import STEPS
from app.workflow.graph import compiled_graph
from app.workflow.nodes import ai_native_nodes
from app.workflow.nodes.ai_native_nodes import (
    route_after_candidate_validation,
    route_after_optimization,
    route_after_repair,
)
from app.workflow.state import WorkflowState


def _failed_state(*, attempts: int = 0) -> WorkflowState:
    return WorkflowState(
        generated_plan={"recipes": []},
        repair_attempts=attempts,
        validation_result={
            "status": "failed",
            "issues": [
                {
                    "code": "ingredient_unresolved",
                    "message": "存在未解析食材",
                    "severity": "error",
                }
            ],
        },
    )


def test_v2_progress_contract_has_nine_real_stages():
    assert len(STEPS) == 9
    assert _find_step_order("recipe_normalization") == 5
    assert _find_step_order("candidate_validation") == 6
    assert _find_step_order("weekly_optimizer") == 7
    assert _find_step_order("plan_aggregation") == 8
    assert _node_to_step_name("weekly_optimizer") == "整周优化"


def test_candidate_failure_enters_bounded_repair_loop():
    state = _failed_state(attempts=0)
    assert route_after_candidate_validation(state) == "repair"

    state.repair_attempts = settings.PLAN_REPAIR_MAX_ATTEMPTS
    assert route_after_candidate_validation(state) == "error_end"
    assert state.generation_error == "存在未解析食材"


def test_optimizer_failure_uses_same_repair_budget():
    state = _failed_state(attempts=0)
    assert route_after_optimization(state) == "repair"

    state.repair_attempts = settings.PLAN_REPAIR_MAX_ATTEMPTS
    assert route_after_optimization(state) == "error_end"


def test_failed_repair_does_not_reuse_the_old_invalid_plan():
    state = _failed_state()
    state.generation_error = "LLM 修复调用失败"
    assert route_after_repair(state) == "error_end"

    state.generation_error = None
    assert route_after_repair(state) == "normalization"


def test_compiled_v2_graph_runs_candidate_to_snapshot_without_recipe_db(monkeypatch):
    candidates = GeneratedPlan.model_validate(
        {
            "recipes": [
                {
                    "name": f"图工作流候选 {index + 1}",
                    "meal_slots": ["breakfast", "lunch", "dinner"],
                    "cuisine_type": f"风格{index % 4}",
                    "ingredients": [
                        {"name": "番茄", "quantity": 100 + index * 5, "unit": "g"},
                        {"name": "鸡蛋", "quantity": 1, "unit": "个"},
                    ],
                    "steps": ["处理食材", "完成烹饪"],
                }
                for index in range(15)
            ]
        }
    )

    async def fake_context(**_kwargs):
        return {"text": "", "meta": {"enabled": False, "used": False, "sources": []}}

    async def fake_generate(**_kwargs):
        return candidates.model_copy(deep=True)

    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    monkeypatch.setattr(ai_native_nodes, "retrieve_generation_context", fake_context)
    monkeypatch.setattr(ai_native_nodes, "generate_plan", fake_generate)

    state = WorkflowState(
        profile_id=1,
        user_input="生成七天三餐，注意多样性",
        duration_days=7,
        total_budget=0,
        skip_intent=True,
        intent_analysis={"meal_count_per_day": 3},
        constraints={
            "diet_type": "balanced",
            "allergen_names": [],
            "calorie_min": 0,
            "calorie_max": 0,
            "target_protein": 0,
            "total_budget": 0,
        },
        ingredient_catalog=load_seed_catalog().model_dump(mode="json"),
    )
    final_state = asyncio.run(compiled_graph.ainvoke(state))

    assert final_state["final_result"]["status"] == "completed"
    assert final_state["aggregated_result"]["schema_version"] == "ai_native_v2"
    assert len(final_state["aggregated_result"]["weekly_plan"]) == 7
    assert final_state["aggregated_result"]["generation_meta"]["unique_recipe_count"] >= 15
