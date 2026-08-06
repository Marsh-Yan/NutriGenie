"""六维评分函数测试"""

from app.services.scoring import health_score, budget_score, preference_score, season_score, variety_score, utilization_score


class TestHealthScore:
    """验证热量匹配度评分"""

    def test_in_range_returns_one(self):
        """热量在目标区间内 → 1.0"""
        score = health_score(recipe_calories=1800, target_min=1700, target_max=2100)
        assert score == 1.0

    def test_at_lower_boundary(self):
        """在区间下限 → 1.0"""
        score = health_score(recipe_calories=1700, target_min=1700, target_max=2100)
        assert score == 1.0

    def test_at_upper_boundary(self):
        """在区间上限 → 1.0"""
        score = health_score(recipe_calories=2100, target_min=1700, target_max=2100)
        assert score == 1.0

    def test_below_by_100(self):
        """低于下限 100kcal → 0.85"""
        score = health_score(recipe_calories=1600, target_min=1700, target_max=2100)
        assert abs(score - 0.85) < 0.01

    def test_below_by_200(self):
        """低于下限 200kcal → 0.70"""
        score = health_score(recipe_calories=1500, target_min=1700, target_max=2100)
        assert abs(score - 0.70) < 0.01

    def test_below_by_700(self):
        """低于下限 700kcal → 0.0（低于 0 分）"""
        score = health_score(recipe_calories=1000, target_min=1700, target_max=2100)
        assert score == 0.0

    def test_above_by_100(self):
        """高于上限 100kcal → 0.85"""
        score = health_score(recipe_calories=2200, target_min=1700, target_max=2100)
        assert abs(score - 0.85) < 0.01

    def test_above_by_200(self):
        """高于上限 200kcal → 0.70"""
        score = health_score(recipe_calories=2300, target_min=1700, target_max=2100)
        assert abs(score - 0.70) < 0.01

    def test_invalid_range_returns_zero(self):
        """无效区间 → 0.0"""
        score = health_score(recipe_calories=1800, target_min=2100, target_max=1700)
        assert score == 0.0

    def test_zero_target_min(self):
        """target_min 为 0 → 0.0"""
        score = health_score(recipe_calories=1800, target_min=0, target_max=2100)
        assert score == 0.0

    def test_zero_calories(self):
        """菜谱热量为 0 → 0.0"""
        score = health_score(recipe_calories=0, target_min=1700, target_max=2100)
        assert score == 0.0

    def test_small_range_precise(self):
        """窄区间：正好在区间内 → 1.0"""
        score = health_score(recipe_calories=150, target_min=140, target_max=160)
        assert score == 1.0

    def test_exactly_midpoint(self):
        """热量正好在区间中间 → 1.0"""
        score = health_score(recipe_calories=1900, target_min=1700, target_max=2100)
        assert score == 1.0

    def test_fractional_penalty(self):
        """不整百的偏离，按比例扣分"""
        score = health_score(recipe_calories=1650, target_min=1700, target_max=2100)
        # 偏离 50kcal → 50/100 * 0.15 = 0.075 → 1 - 0.075 = 0.925
        assert abs(score - 0.925) < 0.01


class TestBudgetScore:
    """验证预算匹配度评分"""

    def test_within_budget_returns_one(self):
        """成本 ≤ 每餐预算 → 1.0"""
        score = budget_score(daily_budget=60, recipe_cost=15, meals_per_day=3)
        assert score == 1.0

    def test_exactly_at_budget(self):
        """成本刚好等于每餐预算 → 1.0"""
        score = budget_score(daily_budget=60, recipe_cost=20, meals_per_day=3)
        assert score == 1.0

    def test_overshoot_by_20_percent(self):
        """超出 20% → 0.80"""
        score = budget_score(daily_budget=60, recipe_cost=24, meals_per_day=3)
        # 每餐预算 20，超出 4 → 20%
        assert abs(score - 0.80) < 0.01

    def test_overshoot_by_50_percent(self):
        """超出 50% → 0.50"""
        score = budget_score(daily_budget=60, recipe_cost=30, meals_per_day=3)
        assert abs(score - 0.50) < 0.01

    def test_overshoot_by_100_percent(self):
        """超出 100% → 0.0"""
        score = budget_score(daily_budget=60, recipe_cost=40, meals_per_day=3)
        assert score == 0.0

    def test_overshoot_by_150_percent(self):
        """超出 150% → 0.0（不低于 0）"""
        score = budget_score(daily_budget=60, recipe_cost=50, meals_per_day=3)
        assert score == 0.0

    def test_no_budget_returns_one(self):
        """每日预算为 0（未设置）→ 1.0"""
        score = budget_score(daily_budget=0, recipe_cost=100, meals_per_day=3)
        assert score == 1.0

    def test_zero_cost_returns_one(self):
        """成本为 0 → 1.0"""
        score = budget_score(daily_budget=60, recipe_cost=0, meals_per_day=3)
        assert score == 1.0

    def test_custom_meals_per_day(self):
        """每日 2 餐，每餐预算更高"""
        # 每日预算 60，2 餐 → 每餐 30
        # 成本 30 → 刚好在预算内
        score = budget_score(daily_budget=60, recipe_cost=30, meals_per_day=2)
        assert score == 1.0

        # 成本 36 → 超出 20% → 0.80
        score = budget_score(daily_budget=60, recipe_cost=36, meals_per_day=2)
        assert abs(score - 0.80) < 0.01

    def test_small_overshoot(self):
        """微超：超出 5% → ~0.95"""
        score = budget_score(daily_budget=60, recipe_cost=21, meals_per_day=3)
        # 每餐 20，超出 1 → 5% → 1.0 - 0.05 = 0.95
        assert abs(score - 0.95) < 0.01


class TestPreferenceScore:
    """验证饮食偏好匹配度评分"""

    def test_balanced_no_tags(self):
        """均衡饮食，无特殊标签 → 基础分 0.50"""
        score = preference_score(
            diet_type="balanced", health_goal="healthy",
            recipe_tags=["家常菜"],
        )
        assert score == 0.50

    def test_fat_loss_with_fat_loss_tag(self):
        """减脂目标 + 减脂标签 → 0.75"""
        score = preference_score(
            diet_type="balanced", health_goal="fat_loss",
            recipe_tags=["减脂", "快手菜"],
        )
        assert abs(score - 0.75) < 0.01

    def test_keto_with_low_carb_tag(self):
        """生酮饮食 + 低碳标签 → 0.75"""
        score = preference_score(
            diet_type="keto", health_goal="healthy",
            recipe_tags=["低碳", "高脂"],
        )
        assert abs(score - 0.75) < 0.01

    def test_high_protein_with_protein_tag(self):
        """高蛋白饮食 + 高蛋白标签 → 0.75"""
        score = preference_score(
            diet_type="high_protein", health_goal="healthy",
            recipe_tags=["高蛋白", "中式经典"],
        )
        assert abs(score - 0.75) < 0.01

    def test_diet_and_goal_both_match(self):
        """饮食类型和健康目标都匹配 → 1.0"""
        score = preference_score(
            diet_type="high_protein", health_goal="muscle_gain",
            recipe_tags=["高蛋白", "低脂", "减脂"],
        )
        assert abs(score - 1.0) < 0.01

    def test_keto_conflict_with_high_carbs(self):
        """生酮饮食 + 高碳水标签 → 0.20"""
        score = preference_score(
            diet_type="keto", health_goal="healthy",
            recipe_tags=["高碳水", "主食"],
        )
        assert abs(score - 0.20) < 0.01

    def test_vegan_with_meat_ingredient(self):
        """素食 + 肉类食材 → 0.0"""
        score = preference_score(
            diet_type="vegan", health_goal="healthy",
            recipe_tags=["家常菜"],
            ingredient_categories=["vegetable", "meat"],
        )
        assert score == 0.0

    def test_vegan_no_meat_ingredient(self):
        """素食 + 全素食材 → 0.50"""
        score = preference_score(
            diet_type="vegan", health_goal="healthy",
            recipe_tags=["家常菜"],
            ingredient_categories=["vegetable", "grain", "condiment"],
        )
        assert score == 0.50

    def test_vegan_tag_match(self):
        """素食 + 素食标签并全素食材 → 0.75"""
        score = preference_score(
            diet_type="vegan", health_goal="healthy",
            recipe_tags=["素食", "家常菜"],
            ingredient_categories=["vegetable", "grain"],
        )
        assert abs(score - 0.75) < 0.01

    def test_no_tags_empty_list(self):
        """无标签 → 基础分"""
        score = preference_score(
            diet_type="balanced", health_goal="healthy",
            recipe_tags=[],
        )
        assert score == 0.50

    def test_score_clamped_to_range(self):
        """分数不会低于 0 或高于 1"""
        score = preference_score(
            diet_type="vegan", health_goal="healthy",
            recipe_tags=["高碳水"],
            ingredient_categories=["meat", "seafood"],
        )
        assert 0.0 <= score <= 1.0


class TestSeasonScore:
    """验证时令匹配度评分"""

    def test_all_in_season(self):
        """所有食材都在当季 → 1.0"""
        score = season_score(
            ingredient_seasons=[["夏季", "秋季"], ["夏季"], ["春季", "夏季"]],
            current_season="夏季",
        )
        assert score == 1.0

    def test_half_in_season(self):
        """一半食材在当季 → 0.5"""
        score = season_score(
            ingredient_seasons=[["夏季"], ["夏季"], ["秋季"], ["春季"]],
            current_season="夏季",
        )
        assert score == 0.5

    def test_none_in_season(self):
        """没有食材在当季 → 0.0"""
        score = season_score(
            ingredient_seasons=[["春季"], ["秋季"], ["冬季"]],
            current_season="夏季",
        )
        assert score == 0.0

    def test_year_round_ingredients(self):
        """全年供应的食材（None）视为当季"""
        score = season_score(
            ingredient_seasons=[None, None, ["夏季"]],
            current_season="夏季",
        )
        assert score == 1.0

    def test_mix_seasonal_and_year_round(self):
        """混合：None + 当季 + 非当季"""
        score = season_score(
            ingredient_seasons=[None, ["夏季"], ["秋季"]],
            current_season="夏季",
        )
        # None → 当季, ["夏季"] → 当季, ["秋季"] → 非当季
        assert abs(score - 2/3) < 0.01

    def test_no_season_data_all_none(self):
        """所有食材都没有季节数据（全 None）→ 1.0"""
        score = season_score(
            ingredient_seasons=[None, None, None],
            current_season="夏季",
        )
        assert score == 1.0

    def test_no_season_data_empty_list(self):
        """空列表视为全年供应"""
        score = season_score(
            ingredient_seasons=[[], [], []],
            current_season="夏季",
        )
        assert score == 1.0

    def test_empty_ingredient_list(self):
        """没有食材 → 1.0"""
        score = season_score(
            ingredient_seasons=[],
            current_season="夏季",
        )
        assert score == 1.0

    def test_multiple_seasons_per_ingredient(self):
        """食材有多个季节标签"""
        score = season_score(
            ingredient_seasons=[["春季", "秋季"], ["春季", "夏季"]],
            current_season="夏季",
        )
        # 第一个不在夏季，第二个在夏季 → 0.5
        assert score == 0.5

    def test_all_out_of_season_has_data(self):
        """所有食材都有季节数据但都不在当季"""
        score = season_score(
            ingredient_seasons=[["春季"], ["冬季"]],
            current_season="夏季",
        )
        assert score == 0.0

    def test_different_season(self):
        """切换季节"""
        score = season_score(
            ingredient_seasons=[["春季"], ["夏季"]],
            current_season="春季",
        )
        assert score == 0.5

        score = season_score(
            ingredient_seasons=[["春季"], ["夏季"]],
            current_season="夏季",
        )
        assert score == 0.5


class TestVarietyScore:
    """验证多样性评分"""

    def test_no_selection_returns_one(self):
        """还没有已选菜谱 → 1.0"""
        score = variety_score(
            recipe_id=1, recipe_category="main_dish", cuisine_type="chinese",
            already_selected=[],
        )
        assert score == 1.0

    def test_same_recipe_penalty(self):
        """同一道菜已选过一次 → -0.50"""
        score = variety_score(
            recipe_id=1, recipe_category="main_dish", cuisine_type="chinese",
            already_selected=[{"recipe_id": 1, "category": "main_dish", "cuisine_type": "chinese", "day": 1}],
        )
        assert abs(score - 0.50) < 0.01

    def test_same_recipe_twice_penalty(self):
        """同一道菜已选过两次 → -1.00 → 0.0"""
        score = variety_score(
            recipe_id=1, recipe_category="main_dish", cuisine_type="chinese",
            already_selected=[
                {"recipe_id": 1, "category": "main_dish", "cuisine_type": "chinese", "day": 1},
                {"recipe_id": 1, "category": "main_dish", "cuisine_type": "chinese", "day": 2},
            ],
        )
        assert score == 0.0

    def test_same_category_penalty(self):
        """同类别已选过 → -0.30"""
        score = variety_score(
            recipe_id=2, recipe_category="main_dish", cuisine_type="chinese",
            already_selected=[{"recipe_id": 1, "category": "main_dish", "cuisine_type": "chinese", "day": 1}],
        )
        assert abs(score - 0.70) < 0.01

    def test_same_category_multiple(self):
        """同类别出现多次 → 叠加扣分"""
        score = variety_score(
            recipe_id=3, recipe_category="main_dish", cuisine_type="chinese",
            already_selected=[
                {"recipe_id": 1, "category": "main_dish", "cuisine_type": "chinese", "day": 1},
                {"recipe_id": 2, "category": "main_dish", "cuisine_type": "chinese", "day": 1},
            ],
        )
        assert abs(score - 0.60) < 0.01

    def test_different_category_ok(self):
        """不同类别 → 不扣分"""
        score = variety_score(
            recipe_id=3, recipe_category="soup", cuisine_type="chinese",
            already_selected=[{"recipe_id": 1, "category": "main_dish", "cuisine_type": "chinese", "day": 1}],
        )
        assert score == 1.0

    def test_cuisine_diversity_ok_under_4(self):
        """同菜系少于 4 次 → 不扣分"""
        score = variety_score(
            recipe_id=3, recipe_category="soup", cuisine_type="chinese",
            already_selected=[
                {"recipe_id": 1, "category": "main_dish", "cuisine_type": "chinese", "day": 1},
                {"recipe_id": 2, "category": "side_dish", "cuisine_type": "chinese", "day": 1},
                {"recipe_id": 4, "category": "main_dish", "cuisine_type": "chinese", "day": 2},
            ],
        )
        assert score == 1.0

    def test_cuisine_diversity_penalty_over_3(self):
        """同菜系超过 3 次 → -0.05/次"""
        score = variety_score(
            recipe_id=5, recipe_category="soup", cuisine_type="chinese",
            already_selected=[
                {"recipe_id": 1, "category": "main_dish", "cuisine_type": "chinese", "day": 1},
                {"recipe_id": 2, "category": "side_dish", "cuisine_type": "chinese", "day": 1},
                {"recipe_id": 3, "category": "main_dish", "cuisine_type": "chinese", "day": 2},
                {"recipe_id": 4, "category": "main_dish", "cuisine_type": "chinese", "day": 2},
            ],
        )
        assert abs(score - 0.95) < 0.01

    def test_mixed_penalties(self):
        """综合叠加"""
        score = variety_score(
            recipe_id=1, recipe_category="main_dish", cuisine_type="chinese",
            already_selected=[
                {"recipe_id": 1, "category": "main_dish", "cuisine_type": "chinese", "day": 1},
                {"recipe_id": 2, "category": "main_dish", "cuisine_type": "chinese", "day": 2},
                {"recipe_id": 3, "category": "main_dish", "cuisine_type": "chinese", "day": 3},
                {"recipe_id": 4, "category": "soup", "cuisine_type": "chinese", "day": 4},
            ],
        )
        assert abs(score - 0.05) < 0.01

    def test_not_below_zero(self):
        """扣分不<0"""
        score = variety_score(
            recipe_id=1, recipe_category="main_dish", cuisine_type="chinese",
            already_selected=[{"recipe_id": 1, "category": "main_dish", "cuisine_type": "chinese", "day": d} for d in range(5)],
        )
        assert score == 0.0


class TestUtilizationScore:
    """验证食材利用率评分"""

    def test_all_covered(self):
        """菜谱所需食材用户全有 → 1.0"""
        score = utilization_score(
            recipe_ingredient_ids=[1, 2, 3],
            owned_ingredient_ids=[1, 2, 3, 4, 5],
        )
        assert score == 1.0

    def test_half_covered(self):
        """用户有 2/4 → 0.50"""
        score = utilization_score(
            recipe_ingredient_ids=[1, 2, 3, 4],
            owned_ingredient_ids=[1, 2, 10],
        )
        assert score == 0.5

    def test_none_covered(self):
        """用户都没有菜谱所需食材 → 0.0"""
        score = utilization_score(
            recipe_ingredient_ids=[1, 2, 3],
            owned_ingredient_ids=[10, 20],
        )
        assert score == 0.0

    def test_one_of_five(self):
        """菜谱要 5 种，用户只有 1 种 → 0.20"""
        score = utilization_score(
            recipe_ingredient_ids=[1, 2, 3, 4, 5],
            owned_ingredient_ids=[1],
        )
        assert abs(score - 0.20) < 0.01

    def test_no_owned(self):
        """用户没列已有食材 → 1.0"""
        score = utilization_score(
            recipe_ingredient_ids=[1, 2, 3],
            owned_ingredient_ids=[],
        )
        assert score == 1.0

    def test_no_recipe_ingredients(self):
        """菜谱没食材信息 → 1.0"""
        score = utilization_score(
            recipe_ingredient_ids=[],
            owned_ingredient_ids=[1, 2],
        )
        assert score == 1.0

    def test_over_one_capped(self):
        """超过 1 封顶为 1.0"""
        score = utilization_score(
            recipe_ingredient_ids=[1, 2],
            owned_ingredient_ids=[1, 2, 3, 4],
        )
        assert score == 1.0

    def test_exact_match(self):
        """菜谱 = 用户有 → 1.0"""
        score = utilization_score(
            recipe_ingredient_ids=[1, 2, 3],
            owned_ingredient_ids=[1, 2, 3],
        )
        assert score == 1.0

    def test_two_of_three(self):
        """菜谱要 3 种，用户有 2 种 → ~0.67"""
        score = utilization_score(
            recipe_ingredient_ids=[1, 2, 3],
            owned_ingredient_ids=[1, 2, 10, 20, 30],
        )
        assert abs(score - 0.67) < 0.01
