"""约束分析服务测试"""

import pytest
from app.models.profile import Profile
from app.services.constraint_analyzer import (
    build_constraints,
    HEALTH_GOAL_ADJUSTMENT,
    DIET_MACRO_SPLIT,
)


@pytest.fixture
def fat_loss_profile():
    """减脂用户画像"""
    return Profile(
        profile_id=1,
        age=28,
        gender="male",
        height=175.0,
        weight=72.0,
        diet_type="balanced",
        health_goal="fat_loss",
        allergies=["海鲜"],
        daily_budget=50.0,
    )


@pytest.fixture
def muscle_gain_profile():
    """增肌用户画像"""
    return Profile(
        profile_id=2,
        age=25,
        gender="female",
        height=165.0,
        weight=60.0,
        diet_type="high_protein",
        health_goal="muscle_gain",
        allergies=["花生", "牛奶"],
        daily_budget=80.0,
    )


@pytest.fixture
def healthy_profile():
    """健康饮食用户画像（无过敏原）"""
    return Profile(
        profile_id=3,
        age=30,
        gender="male",
        height=170.0,
        weight=65.0,
        diet_type="balanced",
        health_goal="healthy",
        allergies=None,
        daily_budget=60.0,
    )


class TestBuildConstraints:
    """验证约束集构建"""

    def test_tdee_calculation(self, fat_loss_profile):
        """TDEE 应该>BMR"""
        c = build_constraints(fat_loss_profile, duration_days=7, total_budget=300)
        assert c.tdee > c.bmr
        assert 2000 < c.tdee < 3000

    def test_calorie_target_for_fat_loss(self, fat_loss_profile):
        """减脂时热量目标 = TDEE × 0.8"""
        c = build_constraints(fat_loss_profile, duration_days=7, total_budget=300)
        expected_adj = HEALTH_GOAL_ADJUSTMENT["fat_loss"]
        assert abs(c.target_calories - c.tdee * expected_adj) <= 1

    def test_calorie_target_for_healthy(self, healthy_profile):
        """健康饮食时热量目标 = TDEE"""
        c = build_constraints(healthy_profile, duration_days=7, total_budget=300)
        expected_adj = HEALTH_GOAL_ADJUSTMENT["healthy"]
        assert abs(c.target_calories - c.tdee * expected_adj) <= 1

    def test_calorie_range(self, healthy_profile):
        """热量范围应在 target ± 150 以内"""
        c = build_constraints(healthy_profile, duration_days=7, total_budget=300)
        assert c.calorie_min <= c.target_calories <= c.calorie_max
        assert c.calorie_max - c.calorie_min == 300
        assert c.calorie_min >= 1000

    def test_protein_for_fat_loss(self, fat_loss_profile):
        """减脂期蛋白质目标 = 体重 × 2.0"""
        c = build_constraints(fat_loss_profile, duration_days=7, total_budget=300)
        expected = 72.0 * 2.0  # 2.0 = PROTEIN_FACTOR["fat_loss"]
        assert abs(c.target_protein - expected) < 0.1

    def test_protein_for_healthy(self, healthy_profile):
        """健康饮食蛋白质目标 = 体重 × 1.2"""
        c = build_constraints(healthy_profile, duration_days=7, total_budget=300)
        expected = 65.0 * 1.2
        assert abs(c.target_protein - expected) < 0.1

    def test_daily_budget(self, fat_loss_profile):
        """每日预算 = 总预算 / 天数"""
        c = build_constraints(fat_loss_profile, duration_days=7, total_budget=300)
        assert c.daily_budget == 42.86  # 300/7 ≈ 42.86
        assert c.total_budget == 300

    def test_daily_budget_single_day(self, healthy_profile):
        """1天规划：每日预算 = 总预算"""
        c = build_constraints(healthy_profile, duration_days=1, total_budget=50)
        assert c.daily_budget == 50.0

    def test_old_profile_budget_does_not_override_unlimited_request(self, healthy_profile):
        c = build_constraints(healthy_profile, duration_days=5, total_budget=0)
        assert c.daily_budget == 0
        assert c.total_budget == 0

    def test_allergen_names(self, fat_loss_profile):
        """应提取过敏原名"""
        c = build_constraints(fat_loss_profile, duration_days=7, total_budget=300)
        assert "海鲜" in c.allergen_names

    def test_no_allergens(self, healthy_profile):
        """无过敏原时为空列表"""
        c = build_constraints(healthy_profile, duration_days=7, total_budget=300)
        assert c.allergen_names == []

    def test_multiple_allergens(self, muscle_gain_profile):
        """多个过敏原"""
        c = build_constraints(muscle_gain_profile, duration_days=7, total_budget=300)
        assert "花生" in c.allergen_names
        assert "牛奶" in c.allergen_names

    def test_request_allergens_merge_without_duplicates(self, fat_loss_profile):
        c = build_constraints(
            fat_loss_profile,
            duration_days=7,
            total_budget=300,
            additional_allergens=["海鲜", "花生"],
        )
        assert c.allergen_names == ["海鲜", "花生"]

    def test_diet_type_macro_split(self, fat_loss_profile):
        """balanced 的配比 = 20%蛋白 / 30%脂肪 / 50%碳水"""
        c = build_constraints(fat_loss_profile, duration_days=7, total_budget=300)
        macro = c.macro_split
        assert macro == DIET_MACRO_SPLIT["balanced"]

    def test_high_protein_macro(self, muscle_gain_profile):
        """high_protein 的配比 = 35%蛋白 / 25%脂肪 / 40%碳水"""
        c = build_constraints(muscle_gain_profile, duration_days=7, total_budget=300)
        assert c.macro_split == DIET_MACRO_SPLIT["high_protein"]

    def test_custom_weight(self, fat_loss_profile):
        """自定义体重"""
        c = build_constraints(fat_loss_profile, duration_days=7, total_budget=300,
                              custom_weight_kg=80.0)
        # TDEE 使用 80kg 而非 profile 的 72kg
        assert c.target_protein > 80  # 蛋白质目标基于 80kg

    def test_custom_activity_factor(self, healthy_profile):
        """自定义活动系数"""
        c_sedentary = build_constraints(healthy_profile, duration_days=7, total_budget=300,
                                         activity_factor=1.2)
        c_active = build_constraints(healthy_profile, duration_days=7, total_budget=300,
                                      activity_factor=1.725)
        assert c_sedentary.tdee < c_active.tdee

    def test_profile_activity_level_is_used(self, healthy_profile):
        healthy_profile.activity_level = "sedentary"
        sedentary = build_constraints(healthy_profile, duration_days=7, total_budget=300)
        healthy_profile.activity_level = "active"
        active = build_constraints(healthy_profile, duration_days=7, total_budget=300)
        assert sedentary.tdee < active.tdee

    def test_excluded_ingredient_ids_empty(self, fat_loss_profile):
        """初始状态下排除食材 ID 列表应为空（由推荐引擎按名称解析）"""
        c = build_constraints(fat_loss_profile, duration_days=7, total_budget=300)
        assert c.excluded_ingredient_ids == []


class TestConstraintSetUtils:
    """验证 ConstraintSet 工具方法"""

    def test_to_dict(self, fat_loss_profile):
        c = build_constraints(fat_loss_profile, duration_days=7, total_budget=300)
        d = c.to_dict()
        assert d["target_calories"] == c.target_calories
        assert d["daily_budget"] == c.daily_budget
        assert d["macro_split"]["protein_pct"] == c.macro_split[0]
        assert d["macro_split"]["fat_pct"] == c.macro_split[1]
        assert d["macro_split"]["carbs_pct"] == c.macro_split[2]
        assert d["health_goal"] == "fat_loss"

    def test_repr(self, fat_loss_profile):
        c = build_constraints(fat_loss_profile, duration_days=7, total_budget=300)
        r = repr(c)
        assert "fat_loss" in r
        assert "balanced" in r
        assert "¥" in r


class TestHealthGoalAdjustments:
    """验证所有健康目标的调整系数合理"""

    def test_fat_loss_below_maintenance(self):
        assert HEALTH_GOAL_ADJUSTMENT["fat_loss"] < 1.0

    def test_muscle_gain_above_maintenance(self):
        assert HEALTH_GOAL_ADJUSTMENT["muscle_gain"] > 1.0

    def test_healthy_maintains(self):
        assert HEALTH_GOAL_ADJUSTMENT["healthy"] == 1.0

    def test_blood_sugar_slightly_below(self):
        assert HEALTH_GOAL_ADJUSTMENT["blood_sugar"] < 1.0


class TestDietMacros:
    """验证所有饮食类型的宏量营养素配比"""

    def test_macro_sums_to_one(self):
        """所有饮食类型的配比加起来应为 1.0"""
        for diet, (p, f, c) in DIET_MACRO_SPLIT.items():
            assert abs(p + f + c - 1.0) < 0.01, f"{diet}: {p}+{f}+{c}={p+f+c} != 1.0"

    def test_keto_is_high_fat(self):
        assert DIET_MACRO_SPLIT["keto"][1] >= 0.55

    def test_vegan_is_higher_carbs(self):
        assert DIET_MACRO_SPLIT["vegan"][2] >= DIET_MACRO_SPLIT["balanced"][2]
