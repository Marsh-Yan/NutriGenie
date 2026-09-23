"""意图分析节点测试"""

from app.workflow.nodes.intent_analyzer import (
    _apply_explicit_intent_overrides,
    _rule_based_parse,
    _sync_explicit_constraints_to_state,
    _merge_edit_intent,
    analyze_intent,
    explicit_budget,
)
import asyncio
from app.workflow.state import WorkflowState


class TestRuleBasedParse:
    """验证规则解析"""

    def test_fat_loss(self):
        result = _rule_based_parse("我准备减脂一周，预算300元")
        assert result["health_goal"] == "fat_loss"
        assert result["duration_days"] == 7
        assert result["total_budget"] == 300.0

    def test_muscle_gain(self):
        result = _rule_based_parse("增肌三天，预算1500")
        assert result["health_goal"] == "muscle_gain"
        assert result["duration_days"] == 3

    def test_muscle_gain_month_becomes_30(self):
        """单次规划最多 30 天"""
        result = _rule_based_parse("增肌三个月")
        assert result["health_goal"] == "muscle_gain"
        assert result["duration_days"] == 30

    def test_blood_sugar(self):
        result = _rule_based_parse("控糖饮食，预算500")
        assert result["health_goal"] == "blood_sugar"

    def test_empty_input(self):
        result = _rule_based_parse("")
        assert result["health_goal"] == "healthy"
        assert result["diet_type"] == "balanced"
        assert result["duration_days"] == 7

    def test_budget_extraction(self):
        result = _rule_based_parse("预算约300元")
        assert result["total_budget"] == 300.0

    def test_budget_no_mention(self):
        result = _rule_based_parse("我想减脂")
        assert result["total_budget"] == 0.0

    def test_budget_without_currency_and_latest_edit(self):
        assert _rule_based_parse("增肌三天，预算200，高蛋白饮食")["total_budget"] == 200
        assert _rule_based_parse("预算300元，本次预算改为200元")["total_budget"] == 200

    def test_appended_local_note_cannot_override_the_main_budget(self):
        assert explicit_budget("预算300元\n已有食材：鸡蛋。\n本地偏好备注：上次预算500元。") == 300

    def test_owned_ingredients(self):
        result = _rule_based_parse("家里有鸡蛋和番茄，预算200")
        assert "鸡蛋" in result["owned_ingredients"]
        assert "番茄" in result["owned_ingredients"]

    def test_owned_ingredients_with_comma(self):
        result = _rule_based_parse("我现有鸡蛋,番茄,鸡胸肉")
        assert "鸡蛋" in result["owned_ingredients"]
        assert "番茄" in result["owned_ingredients"]

    def test_duration_variations(self):
        """不同天数表达"""
        assert _rule_based_parse("三天方案")["duration_days"] == 3
        assert _rule_based_parse("五天")["duration_days"] == 5
        assert _rule_based_parse("7天")["duration_days"] == 7

    def test_diet_type_keto(self):
        result = _rule_based_parse("生酮饮食")
        assert result["diet_type"] == "keto"

    def test_diet_type_vegan(self):
        result = _rule_based_parse("素食")
        assert result["diet_type"] == "vegan"

    def test_diet_type_high_protein(self):
        result = _rule_based_parse("高蛋白饮食，增肌")
        assert result["diet_type"] == "high_protein"
        assert result["health_goal"] == "muscle_gain"

    def test_allergies(self):
        result = _rule_based_parse("不吃海鲜，预算300")
        assert result["allergies_or_concerns"] is not None
        assert "海鲜" in result["allergies_or_concerns"]

    def test_default_meal_count(self):
        result = _rule_based_parse("减脂一周")
        assert result["meal_count_per_day"] == 3

    def test_explicit_meal_count(self):
        result = _rule_based_parse("每天两餐，减脂一周")
        assert result["meal_count_per_day"] == 2

    def test_full_parse(self):
        """完整输入解析"""
        result = _rule_based_parse(
            "我准备减脂一周，预算300元，家里有鸡蛋和番茄，不吃海鲜"
        )
        assert result["health_goal"] == "fat_loss"
        assert result["duration_days"] == 7
        assert result["total_budget"] == 300.0
        assert "鸡蛋" in result["owned_ingredients"]
        assert "番茄" in result["owned_ingredients"]
        assert result["allergies_or_concerns"] is not None


class TestExplicitIntentOverrides:
    def test_explicit_fat_loss_overrides_conflicting_llm_goal(self):
        merged = _apply_explicit_intent_overrides(
            "我想减脂，预算300元",
            {"health_goal": "healthy", "diet_type": "balanced"},
        )
        assert merged["health_goal"] == "fat_loss"

    def test_explicit_diet_overrides_conflicting_llm_diet(self):
        merged = _apply_explicit_intent_overrides(
            "我要生酮饮食",
            {"health_goal": "healthy", "diet_type": "balanced"},
        )
        assert merged["diet_type"] == "keto"

    def test_text_constraints_sync_to_workflow_state(self):
        state = WorkflowState(
            user_input="减脂五天，预算500元",
            duration_days=7,
            total_budget=300,
        )
        _sync_explicit_constraints_to_state(
            state, {"duration_days": 5, "total_budget": 500}
        )
        assert state.duration_days == 5
        assert state.total_budget == 500

    def test_budget_with_spaces_is_authoritative(self):
        state = WorkflowState(user_input="减脂三天，预算 180 元", total_budget=300)
        parsed = _rule_based_parse(state.user_input)
        _sync_explicit_constraints_to_state(state, parsed)
        assert state.duration_days == 3
        assert state.total_budget == 180

    def test_numeric_budget_remains_authoritative_when_text_omits_it(self):
        state = WorkflowState(user_input="减脂三天", total_budget=300)
        parsed = {"total_budget": 0}
        _sync_explicit_constraints_to_state(state, parsed)
        assert parsed["total_budget"] == 300


class TestStateCreation:
    """验证 WorkflowState 创建"""

    def test_default_values(self):
        state = WorkflowState()
        assert state.duration_days == 7
        assert state.total_budget == 0.0
        assert state.owned_ingredient_ids == []
        assert state.current_node == "intent_analyzer"
        assert state.errors == []

    def test_with_input(self):
        state = WorkflowState(
            profile_id=1,
            user_input="减脂一周，预算300",
            duration_days=7,
            total_budget=300,
        )
        assert state.profile_id == 1
        assert state.total_budget == 300.0


def test_reused_intent_snapshot_is_not_overwritten():
    state = WorkflowState(
        user_input="减脂一周，预算300元",
        skip_intent=True,
        intent_analysis={"health_goal": "muscle_gain", "meal_count_per_day": 3},
    )
    result = asyncio.run(analyze_intent(state))
    assert result.intent_analysis["health_goal"] == "muscle_gain"


def test_budget_edit_preserves_previous_goal_diet_and_allergy():
    previous = {
        "health_goal": "muscle_gain", "diet_type": "high_protein",
        "allergies_or_concerns": "花生", "total_budget": 300,
        "meal_count_per_day": 3,
    }
    parsed = _rule_based_parse("预算改为200元")
    merged = _merge_edit_intent(previous, parsed, "预算改为200元")
    assert merged["total_budget"] == 200
    assert merged["health_goal"] == "muscle_gain"
    assert merged["diet_type"] == "high_protein"
    assert merged["allergies_or_concerns"] == "花生"
