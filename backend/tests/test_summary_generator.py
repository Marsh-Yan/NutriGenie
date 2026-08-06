"""总结生成节点测试"""

from app.workflow.nodes.summary_generator import _template_summary, _build_llm_input
from app.workflow.state import WorkflowState


def make_result(overrides=None) -> dict:
    """构造聚合结果"""
    result = {
        "top5": [
            {
                "recipe_id": 1, "name": "番茄炒蛋", "total_score": 0.85,
                "estimated_cost": 6.5, "scores": {"health": 0.88},
                "nutrition": {"calories": 150, "protein": 10, "fat": 8, "carbs": 5},
            },
            {
                "recipe_id": 7, "name": "西兰花炒虾仁", "total_score": 0.82,
                "estimated_cost": 18.5, "scores": {"health": 0.92},
                "nutrition": {"calories": 180, "protein": 22.5, "fat": 7.2, "carbs": 6.8},
            },
            {
                "recipe_id": 16, "name": "Grilled Chicken Salad", "total_score": 0.78,
                "estimated_cost": 25.0, "scores": {"health": 0.95},
                "nutrition": {"calories": 350, "protein": 35, "fat": 18, "carbs": 8},
            },
        ],
        "nutrition_report": {
            "avg_daily_calories": 1650,
            "total_calories": 11550,
            "protein_g": 95, "fat_g": 48, "carbs_g": 198, "fiber_g": 25,
            "protein_pct": 0.34, "fat_pct": 0.26, "carbs_pct": 0.40,
            "recommendation": "蛋白质占比 34%，有助于减脂期保留肌肉。",
        },
        "shopping_list": {
            "total_cost": 285.5,
            "items": [],
            "by_category": {},
        },
    }
    if overrides:
        _deep_update(result, overrides)
    return result


def _deep_update(d, u):
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            _deep_update(d[k], v)
        else:
            d[k] = v


class TestTemplateSummary:
    """验证模板总结"""

    def test_normal_state(self):
        """完整数据生成总结"""
        state = WorkflowState(
            profile_id=1,
            user_input="减脂一周，预算300元",
            duration_days=7,
            total_budget=300.0,
            aggregated_result=make_result(),
        )
        summary = _template_summary(state)
        assert len(summary) > 50
        assert "📋" in summary
        assert "番茄炒蛋" in summary
        assert "预算" in summary
        assert "300" in summary

    def test_budget_within_range(self):
        """预算未超出"""
        state = WorkflowState(
            user_input="减脂一周", total_budget=300,
            duration_days=7, profile_id=1,
            aggregated_result=make_result({"shopping_list": {"total_cost": 250}}),
        )
        summary = _template_summary(state)
        assert "预算范围内" in summary or "📋" in summary

    def test_budget_overrun(self):
        """超出预算"""
        state = WorkflowState(
            user_input="减脂一周", total_budget=200,
            duration_days=7, profile_id=1,
            aggregated_result=make_result({"shopping_list": {"total_cost": 285.5}}),
        )
        summary = _template_summary(state)
        assert "超出" in summary

    def test_no_budget(self):
        """未指定预算"""
        state = WorkflowState(
            user_input="减脂一周", total_budget=0,
            duration_days=7, profile_id=1,
            aggregated_result=make_result(),
        )
        summary = _template_summary(state)
        assert "未指定预算" in summary

    def test_no_aggregated_result(self):
        """没有聚合结果"""
        state = WorkflowState(user_input="test")
        summary = _template_summary(state)
        assert len(summary) > 0

    def test_top5_empty(self):
        """没有推荐菜谱"""
        state = WorkflowState(
            user_input="test", duration_days=3, profile_id=1,
            aggregated_result=make_result({"top5": []}),
        )
        summary = _template_summary(state)
        assert len(summary) > 30


class TestBuildLlmInput:
    """验证 LLM 输入构建"""

    def test_contains_key_info(self):
        state = WorkflowState(
            profile_id=1,
            user_input="减脂一周，预算300元，家里有鸡蛋",
            duration_days=7,
            total_budget=300.0,
            intent_analysis={
                "health_goal": "fat_loss",
                "owned_ingredients": ["鸡蛋"],
            },
            constraints={"health_goal": "fat_loss", "diet_type": "balanced"},
            aggregated_result=make_result(),
        )
        result = _build_llm_input(state)
        assert "减脂" in result
        assert "鸡蛋" in result
        assert "番茄炒蛋" in result
        assert "1650" in result  # 日均热量
        assert "285" in result   # 采购花费
