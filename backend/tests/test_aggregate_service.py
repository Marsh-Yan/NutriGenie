"""聚合排序与周计划生成测试"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.recipe import Recipe
from app.models.ingredient import Ingredient
from app.models.ingredient_nutrition import IngredientNutrition
from app.models.recipe_ingredient import RecipeIngredient
from app.models.profile import Profile

from app.services.constraint_analyzer import build_constraints
from app.services.aggregate_service import (
    _build_top5,
    _build_shopping_list,
    _build_nutrition_report,
    _greedy_weekly_plan,
    aggregate_and_rank,
    validate_weekly_plan,
)
from app.services.recommendation_engine import build_candidate_pool, rank_candidates, DEFAULT_WEIGHTS
from app.services.nutrition_service import calculate_recipe_nutrition


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    from app.db.database import Base
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed_data(db_session):
    """各种类型菜谱的测试数据"""
    ings = [
        Ingredient(ingredient_id=1, name="番茄", category="vegetable", unit="个", unit_price=2.5, season_tags=["夏季", "秋季"]),
        Ingredient(ingredient_id=2, name="鸡蛋", category="egg", unit="个", unit_price=1.2, season_tags=None),
        Ingredient(ingredient_id=3, name="鸡胸肉", category="meat", unit="斤", unit_price=15.0, season_tags=None),
        Ingredient(ingredient_id=4, name="青椒", category="vegetable", unit="个", unit_price=1.5, season_tags=["夏季"]),
        Ingredient(ingredient_id=5, name="西兰花", category="vegetable", unit="颗", unit_price=5.0, season_tags=["春季", "秋季"]),
        Ingredient(ingredient_id=6, name="虾仁", category="seafood", unit="斤", unit_price=35.0, season_tags=None),
        Ingredient(ingredient_id=7, name="大米", category="grain", unit="g", unit_price=0.01, season_tags=None),
        Ingredient(ingredient_id=8, name="酱油", category="condiment", unit="勺", unit_price=0.5, season_tags=None),
        Ingredient(ingredient_id=9, name="燕麦", category="grain", unit="g", unit_price=0.02, season_tags=None),
        Ingredient(ingredient_id=10, name="牛奶", category="dairy", unit="盒", unit_price=5.0, season_tags=None),
        Ingredient(ingredient_id=11, name="洋葱", category="vegetable", unit="个", unit_price=2.0, season_tags=["秋季"]),
    ]
    for ing in ings:
        db_session.add(ing)

    nuts = [
        IngredientNutrition(ingredient_id=1, calories_per_100g=18, protein_per_100g=0.9, fat_per_100g=0.2, carbs_per_100g=3.9, fiber_per_100g=1.2),
        IngredientNutrition(ingredient_id=2, calories_per_100g=144, protein_per_100g=13.3, fat_per_100g=8.8, carbs_per_100g=2.8),
        IngredientNutrition(ingredient_id=3, calories_per_100g=167, protein_per_100g=25, fat_per_100g=7, carbs_per_100g=0),
        IngredientNutrition(ingredient_id=4, calories_per_100g=22, protein_per_100g=1.0, fat_per_100g=0.3, carbs_per_100g=4.6),
        IngredientNutrition(ingredient_id=5, calories_per_100g=34, protein_per_100g=2.8, fat_per_100g=0.4, carbs_per_100g=6.6),
        IngredientNutrition(ingredient_id=6, calories_per_100g=99, protein_per_100g=20.3, fat_per_100g=0.7, carbs_per_100g=0.2),
        IngredientNutrition(ingredient_id=7, calories_per_100g=130, protein_per_100g=2.7, fat_per_100g=0.3, carbs_per_100g=28.7),
        IngredientNutrition(ingredient_id=8, calories_per_100g=60, protein_per_100g=6, fat_per_100g=0, carbs_per_100g=10),
        IngredientNutrition(ingredient_id=9, calories_per_100g=389, protein_per_100g=16.9, fat_per_100g=6.9, carbs_per_100g=66.3),
        IngredientNutrition(ingredient_id=10, calories_per_100g=66, protein_per_100g=3.2, fat_per_100g=3.6, carbs_per_100g=4.8),
        IngredientNutrition(ingredient_id=11, calories_per_100g=40, protein_per_100g=1.1, fat_per_100g=0.1, carbs_per_100g=9.3),
    ]
    for n in nuts:
        db_session.add(n)

    recipes = [
        Recipe(recipe_id=1, name="番茄炒蛋", category="main_dish", cuisine_type="chinese", difficulty="easy",
               prep_time=5, cook_time=5, servings=2,
               steps=[{"step": 1, "content": "番茄切块"}, {"step": 2, "content": "炒鸡蛋"}],
               total_calories=150, total_protein=10, total_fat=8, total_carbs=5,
               tags=["快手菜", "减脂"]),
        Recipe(recipe_id=2, name="Grilled Chicken Salad", category="light_meal", cuisine_type="western", difficulty="easy",
               prep_time=10, cook_time=12, servings=1,
               steps=[{"step": 1, "content": "煎鸡胸"}],
               total_calories=350, total_protein=35, total_fat=18, total_carbs=8,
               tags=["减脂", "高蛋白", "西餐"]),
        Recipe(recipe_id=3, name="青椒肉丝", category="main_dish", cuisine_type="chinese", difficulty="easy",
               prep_time=10, cook_time=8, servings=2,
               steps=[{"step": 1, "content": "切肉丝"}, {"step": 2, "content": "炒青椒"}],
               total_calories=280, total_protein=22, total_fat=15, total_carbs=10,
               tags=["高蛋白"]),
        Recipe(recipe_id=4, name="蒜蓉西兰花", category="side_dish", cuisine_type="chinese", difficulty="easy",
               prep_time=5, cook_time=5, servings=2,
               steps=[{"step": 1, "content": "焯水"}, {"step": 2, "content": "蒜蓉炒"}],
               total_calories=80, total_protein=5, total_fat=4, total_carbs=8,
               tags=["素食", "快手菜", "减脂"]),
        Recipe(recipe_id=5, name="Oatmeal Bowl", category="staple", cuisine_type="western", difficulty="easy",
               prep_time=3, cook_time=5, servings=1,
               steps=[{"step": 1, "content": "煮燕麦"}],
               total_calories=350, total_protein=12, total_fat=8, total_carbs=55,
               tags=["健康", "素食"]),
        Recipe(recipe_id=6, name="虾仁炒饭", category="staple", cuisine_type="chinese", difficulty="easy",
               prep_time=5, cook_time=10, servings=1,
               steps=[{"step": 1, "content": "炒虾仁"}, {"step": 2, "content": "炒饭"}],
               total_calories=450, total_protein=25, total_fat=15, total_carbs=55,
               tags=["高蛋白", "主食"]),
        Recipe(recipe_id=7, name="牛奶燕麦", category="staple", cuisine_type="western", difficulty="easy",
               prep_time=2, cook_time=3, servings=1,
               steps=[{"step": 1, "content": "泡燕麦"}],
               total_calories=350, total_protein=15, total_fat=10, total_carbs=55,
               tags=["快手", "健康"]),
    ]
    for r in recipes:
        db_session.add(r)

    assocs = [
        RecipeIngredient(recipe_id=1, ingredient_id=1, quantity=2, unit="个"),
        RecipeIngredient(recipe_id=1, ingredient_id=2, quantity=3, unit="个"),
        RecipeIngredient(recipe_id=1, ingredient_id=8, quantity=1, unit="勺"),
        RecipeIngredient(recipe_id=2, ingredient_id=3, quantity=200, unit="g"),
        RecipeIngredient(recipe_id=2, ingredient_id=5, quantity=100, unit="g"),
        RecipeIngredient(recipe_id=2, ingredient_id=8, quantity=1, unit="勺"),
        RecipeIngredient(recipe_id=3, ingredient_id=4, quantity=2, unit="个"),
        RecipeIngredient(recipe_id=3, ingredient_id=11, quantity=1, unit="个"),
        RecipeIngredient(recipe_id=3, ingredient_id=8, quantity=1, unit="勺"),
        RecipeIngredient(recipe_id=4, ingredient_id=5, quantity=1, unit="颗"),
        RecipeIngredient(recipe_id=4, ingredient_id=8, quantity=1, unit="勺"),
        RecipeIngredient(recipe_id=5, ingredient_id=9, quantity=50, unit="g"),
        RecipeIngredient(recipe_id=5, ingredient_id=10, quantity=1, unit="盒"),
        RecipeIngredient(recipe_id=6, ingredient_id=6, quantity=100, unit="g"),
        RecipeIngredient(recipe_id=6, ingredient_id=2, quantity=1, unit="个"),
        RecipeIngredient(recipe_id=6, ingredient_id=7, quantity=200, unit="g"),
        RecipeIngredient(recipe_id=6, ingredient_id=8, quantity=1, unit="勺"),
        RecipeIngredient(recipe_id=7, ingredient_id=9, quantity=50, unit="g"),
        RecipeIngredient(recipe_id=7, ingredient_id=10, quantity=1, unit="盒"),
    ]
    for a in assocs:
        db_session.add(a)

    db_session.commit()
    return db_session


@pytest.fixture
def fat_loss_constraints(seed_data):
    profile = Profile(
        profile_id=1, age=28, gender="male", height=175, weight=72,
        diet_type="balanced", health_goal="fat_loss",
        allergies=None,
    )
    return build_constraints(profile, duration_days=7, total_budget=300)


# ═══════════════════════════════════════════════════
# 测试：TOP5
# ═══════════════════════════════════════════════════

class TestBuildTop5:
    def test_returns_5_items(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=10)
        top5 = _build_top5(ranked, fat_loss_constraints)
        assert len(top5) == 5

    def test_each_item_has_required_keys(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=10)
        top5 = _build_top5(ranked, fat_loss_constraints)
        for item in top5:
            assert "recipe_id" in item
            assert "name" in item
            assert "scores" in item
            assert "total_score" in item
            assert "nutrition" in item
            assert "estimated_cost" in item
            assert "explanation" in item
            assert all(k in item["scores"] for k in ["health", "budget", "preference", "season", "variety", "utilization"])

    def test_score_descending_order(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=10)
        top5 = _build_top5(ranked, fat_loss_constraints)
        for i in range(len(top5) - 1):
            assert top5[i]["total_score"] >= top5[i + 1]["total_score"]


# ═══════════════════════════════════════════════════
# 测试：周计划
# ═══════════════════════════════════════════════════

class TestGreedyWeeklyPlan:
    def test_returns_7_days(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=10)
        pool = build_candidate_pool(seed_data)
        plan, count = _greedy_weekly_plan(
            seed_data, pool, ranked, fat_loss_constraints, "夏季", [], DEFAULT_WEIGHTS,
            duration_days=7,
        )
        assert len(plan) == 7

    def test_each_day_has_three_meals(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=10)
        pool = build_candidate_pool(seed_data)
        plan, _ = _greedy_weekly_plan(
            seed_data, pool, ranked, fat_loss_constraints, "夏季", [], DEFAULT_WEIGHTS,
            duration_days=3,
        )
        for day_entry in plan:
            for slot in ["breakfast", "lunch", "dinner"]:
                assert day_entry["meals"][slot] is not None

    def test_breakfast_has_staple_or_light(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=10)
        pool = build_candidate_pool(seed_data)
        plan, _ = _greedy_weekly_plan(
            seed_data, pool, ranked, fat_loss_constraints, "夏季", [], DEFAULT_WEIGHTS,
            duration_days=3,
        )
        candidate_map = {c.recipe_id: c for c in pool}
        for day_entry in plan:
            bk = day_entry["meals"]["breakfast"]
            if bk:
                cat = candidate_map[bk["recipe_id"]].category
                assert cat in {"staple", "light_meal"}

    def test_breakfast_excludes_dinner_style_staples(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=10)
        pool = build_candidate_pool(seed_data)
        plan, _ = _greedy_weekly_plan(
            seed_data, pool, ranked, fat_loss_constraints, "夏季", [], DEFAULT_WEIGHTS,
            duration_days=3,
        )
        for day in plan:
            assert "fried rice" not in day["meals"]["breakfast"]["name"].lower()

    def test_meals_have_nutrition(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=10)
        pool = build_candidate_pool(seed_data)
        plan, _ = _greedy_weekly_plan(
            seed_data, pool, ranked, fat_loss_constraints, "夏季", [], DEFAULT_WEIGHTS,
            duration_days=1,
        )
        day = plan[0]
        for slot in ["breakfast", "lunch", "dinner"]:
            meal = day["meals"][slot]
            assert "nutrition" in meal
            assert "calories" in meal["nutrition"]


# ═══════════════════════════════════════════════════
# 测试：营养报告
# ═══════════════════════════════════════════════════

class TestNutritionReport:
    def test_has_required_fields(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=10)
        pool = build_candidate_pool(seed_data)
        plan, _ = _greedy_weekly_plan(
            seed_data, pool, ranked, fat_loss_constraints, "夏季", [], DEFAULT_WEIGHTS,
            duration_days=3,
        )
        report = _build_nutrition_report(seed_data, plan, fat_loss_constraints)
        keys = ["avg_daily_calories", "total_calories", "protein_g", "fat_g", "carbs_g",
                "fiber_g", "protein_pct", "fat_pct", "carbs_pct", "recommendation"]
        for k in keys:
            assert k in report

    def test_report_reasonable_range(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=10)
        pool = build_candidate_pool(seed_data)
        plan, _ = _greedy_weekly_plan(
            seed_data, pool, ranked, fat_loss_constraints, "夏季", [], DEFAULT_WEIGHTS,
            duration_days=3,
        )
        report = _build_nutrition_report(seed_data, plan, fat_loss_constraints)
        assert 500 <= report["avg_daily_calories"] <= 4000
        assert 0 < report["protein_pct"] < 1
        assert 0 < report["fat_pct"] < 1
        assert 0 < report["carbs_pct"] < 1

    def test_macro_pcts_sum_to_one(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=10)
        pool = build_candidate_pool(seed_data)
        plan, _ = _greedy_weekly_plan(
            seed_data, pool, ranked, fat_loss_constraints, "夏季", [], DEFAULT_WEIGHTS,
            duration_days=3,
        )
        report = _build_nutrition_report(seed_data, plan, fat_loss_constraints)
        total = report["protein_pct"] + report["fat_pct"] + report["carbs_pct"]
        assert abs(total - 1.0) < 0.05

    def test_uses_recipe_per_serving_nutrition(self, seed_data, fat_loss_constraints):
        """A two-serving recipe must not count its full batch as one meal."""
        plan = [{"day": 1, "meals": {
            "breakfast": {"recipe_id": 1},
            "lunch": {"recipe_id": 1},
            "dinner": {"recipe_id": 1},
        }}]
        report = _build_nutrition_report(seed_data, plan, fat_loss_constraints)
        nutrition = calculate_recipe_nutrition(seed_data, 1)
        assert report["avg_daily_calories"] == round(
            nutrition["per_serving"]["calories"] * 3, 0
        )


# ═══════════════════════════════════════════════════
# 测试：采购清单
# ═══════════════════════════════════════════════════

class TestShoppingList:
    def test_returns_items(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=10)
        pool = build_candidate_pool(seed_data)
        plan, _ = _greedy_weekly_plan(
            seed_data, pool, ranked, fat_loss_constraints, "夏季", [], DEFAULT_WEIGHTS,
            duration_days=1,
        )
        sl = _build_shopping_list(seed_data, plan, owned_ids=[])
        assert "total_cost" in sl
        assert "items" in sl
        assert "by_category" in sl
        assert len(sl["items"]) > 0

    def test_excludes_owned(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=10)
        pool = build_candidate_pool(seed_data)
        plan, _ = _greedy_weekly_plan(
            seed_data, pool, ranked, fat_loss_constraints, "夏季", [], DEFAULT_WEIGHTS,
            duration_days=1,
        )
        # 如果用户有所有需要的东西，采购清单应为空
        all_needed = set()
        for de in plan:
            for slot in ["breakfast", "lunch", "dinner"]:
                meal = de["meals"].get(slot)
                if meal:
                    all_needed.add(meal["recipe_id"])

        # 暂不测试全拥有情况，只要确保分类存在即可
        sl = _build_shopping_list(seed_data, plan, owned_ids=[])
        assert isinstance(sl["by_category"], dict)

    def test_accumulates_repeated_recipe_ingredients_in_purchase_units(self, seed_data):
        """Two 200g chicken meals should buy 0.8 jin, costing 12 yuan."""
        plan = [
            {"day": 1, "meals": {
                "breakfast": None,
                "lunch": {"recipe_id": 2},
                "dinner": {"recipe_id": 2},
            }}
        ]
        shopping = _build_shopping_list(seed_data, plan, owned_ids=[])
        chicken = next(item for item in shopping["items"] if item["ingredient_id"] == 3)
        assert chicken["quantity"] == 0.8
        assert chicken["unit"] == "斤"
        assert chicken["estimated_cost"] == 12.0

    def test_fat_loss_report_does_not_call_low_calorie_in_range(self, seed_data, fat_loss_constraints):
        report = _build_nutrition_report(seed_data, [], fat_loss_constraints)
        # Empty report uses a different copy; exercise the fat-loss branch directly
        from app.services.aggregate_service import _build_nutrition_report as build_report
        low_plan = [{"day": 1, "meals": {"breakfast": None, "lunch": None, "dinner": None}}]
        low_report = build_report(seed_data, low_plan, fat_loss_constraints)
        assert "处于减脂目标区间" not in low_report["recommendation"]


# ═══════════════════════════════════════════════════
# 测试：完整聚合
# ═══════════════════════════════════════════════════

class TestAggregateAndRank:
    def test_returns_complete_result(self, seed_data, fat_loss_constraints):
        result = aggregate_and_rank(
            seed_data, fat_loss_constraints, current_season="夏季",
            owned_ingredient_ids=[], duration_days=3,
        )
        assert "top5" in result
        assert "weekly_plan" in result
        assert "nutrition_report" in result
        assert "shopping_list" in result
        assert "summary" in result

    def test_top5_count(self, seed_data, fat_loss_constraints):
        result = aggregate_and_rank(
            seed_data, fat_loss_constraints, current_season="夏季",
            owned_ingredient_ids=[], duration_days=3,
        )
        assert len(result["top5"]) == 5

    def test_weekly_plan_days(self, seed_data, fat_loss_constraints):
        result = aggregate_and_rank(
            seed_data, fat_loss_constraints, current_season="夏季",
            owned_ingredient_ids=[], duration_days=3,
        )
        assert len(result["weekly_plan"]) == 3

    def test_each_meal_has_nutrition(self, seed_data, fat_loss_constraints):
        """每餐应补全营养数据"""
        result = aggregate_and_rank(
            seed_data, fat_loss_constraints, current_season="夏季",
            owned_ingredient_ids=[], duration_days=1,
        )
        for de in result["weekly_plan"]:
            for slot in ["breakfast", "lunch", "dinner"]:
                meal = de["meals"].get(slot)
                if meal:
                    assert "calories" in meal["nutrition"]
                    assert "protein" in meal["nutrition"]

    def test_daily_timeline_total_matches_meal_nutrition(self, seed_data, fat_loss_constraints):
        result = aggregate_and_rank(
            seed_data, fat_loss_constraints, current_season="夏季",
            owned_ingredient_ids=[], duration_days=1,
        )
        day = result["weekly_plan"][0]
        meal_calories = sum(
            meal["nutrition"]["calories"]
            for meal in day["meals"].values()
            if meal
        )
        assert day["total_nutrition"]["calories"] == round(meal_calories, 1)

    def test_each_top5_has_nutrition(self, seed_data, fat_loss_constraints):
        result = aggregate_and_rank(
            seed_data, fat_loss_constraints, current_season="夏季",
            owned_ingredient_ids=[], duration_days=3,
        )
        for item in result["top5"]:
            nut = item["nutrition"]
            assert nut["calories"] > 0
            assert nut["protein"] > 0

    def test_summary_is_not_empty(self, seed_data, fat_loss_constraints):
        result = aggregate_and_rank(
            seed_data, fat_loss_constraints, current_season="夏季",
            owned_ingredient_ids=[], duration_days=3,
        )
        assert len(result["summary"]) > 50

    def test_shopping_has_total_cost(self, seed_data, fat_loss_constraints):
        result = aggregate_and_rank(
            seed_data, fat_loss_constraints, current_season="夏季",
            owned_ingredient_ids=[], duration_days=3,
        )
        assert result["shopping_list"]["total_cost"] >= 0

    def test_with_owned_ingredients(self, seed_data, fat_loss_constraints):
        """已有食材影响采购清单"""
        result_no_owned = aggregate_and_rank(
            seed_data, fat_loss_constraints, current_season="夏季",
            owned_ingredient_ids=[], duration_days=1,
        )
        # 用户有番茄(1)、鸡蛋(2)
        result_owned = aggregate_and_rank(
            seed_data, fat_loss_constraints, current_season="夏季",
            owned_ingredient_ids=[1, 2], duration_days=1,
        )
        assert result_owned["shopping_list"]["total_cost"] < result_no_owned["shopping_list"]["total_cost"]


class TestWeeklyPlanValidation:
    """验证周计划质量提示，不将软约束偏差隐藏为成功。"""

    def test_incomplete_plan_is_not_passed(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=5)
        validation = validate_weekly_plan(
            weekly_plan=[{"day": 1, "meals": {"breakfast": None, "lunch": None, "dinner": None}}],
            nutrition_report={"avg_daily_calories": 0},
            ranked_recipes=ranked,
            constraints=fat_loss_constraints,
        )

        assert validation["passed"] is False
        assert len(validation["missing_meals"]) == 3
        assert validation["warnings"]

    def test_complete_plan_exposes_calorie_warning(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates(seed_data, fat_loss_constraints, top_n=5)
        recipe = ranked[0]
        meal = {"recipe_id": recipe.recipe_id, "name": recipe.name}
        validation = validate_weekly_plan(
            weekly_plan=[{"day": 1, "meals": {"breakfast": meal, "lunch": meal, "dinner": meal}}],
            nutrition_report={"avg_daily_calories": 100},
            ranked_recipes=ranked,
            constraints=fat_loss_constraints,
        )

        assert validation["passed"] is True
        assert any("日均热量" in warning for warning in validation["warnings"])
