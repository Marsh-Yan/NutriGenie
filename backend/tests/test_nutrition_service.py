"""营养计算服务测试"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.recipe import Recipe
from app.models.ingredient import Ingredient
from app.models.ingredient_nutrition import IngredientNutrition
from app.models.recipe_ingredient import RecipeIngredient

from app.services.nutrition_service import (
    get_estimated_grams,
    calculate_recipe_nutrition,
    calculate_nutrition_for_meals,
)


# ─── 测试用内存数据库 ─────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed_data(db_session):
    """插入测试数据"""
    # 食材
    ings = [
        Ingredient(ingredient_id=1, name="番茄", category="vegetable", unit="个", unit_price=2.5),
        Ingredient(ingredient_id=2, name="鸡蛋", category="egg", unit="个", unit_price=1.2),
        Ingredient(ingredient_id=3, name="鸡胸肉", category="meat", unit="斤", unit_price=15.0),
        Ingredient(ingredient_id=5, name="西兰花", category="vegetable", unit="颗", unit_price=5.0),
        Ingredient(ingredient_id=7, name="大米", category="grain", unit="g", unit_price=0.01),
        Ingredient(ingredient_id=8, name="酱油", category="condiment", unit="勺", unit_price=0.5),
    ]
    for ing in ings:
        db_session.add(ing)

    # 营养数据（每100g）
    nuts = [
        IngredientNutrition(ingredient_id=1, calories_per_100g=18, protein_per_100g=0.9, fat_per_100g=0.2, carbs_per_100g=3.9, fiber_per_100g=1.2),
        IngredientNutrition(ingredient_id=2, calories_per_100g=144, protein_per_100g=13.3, fat_per_100g=8.8, carbs_per_100g=2.8, fiber_per_100g=0),
        IngredientNutrition(ingredient_id=3, calories_per_100g=167, protein_per_100g=25, fat_per_100g=7, carbs_per_100g=0, fiber_per_100g=0),
        IngredientNutrition(ingredient_id=5, calories_per_100g=34, protein_per_100g=2.8, fat_per_100g=0.4, carbs_per_100g=6.6, fiber_per_100g=2.6),
        IngredientNutrition(ingredient_id=7, calories_per_100g=130, protein_per_100g=2.7, fat_per_100g=0.3, carbs_per_100g=28.7, fiber_per_100g=0.4),
        IngredientNutrition(ingredient_id=8, calories_per_100g=60, protein_per_100g=6, fat_per_100g=0, carbs_per_100g=10, fiber_per_100g=0),
    ]
    for n in nuts:
        db_session.add(n)

    # 菜谱
    recipes = [
        Recipe(
            recipe_id=1, name="番茄炒蛋", category="main_dish", cuisine_type="chinese",
            prep_time=5, cook_time=5, servings=2,
            steps=[{"step": 1, "content": "番茄切块"}, {"step": 2, "content": "炒鸡蛋"}],
            total_calories=150, total_protein=10, total_fat=8, total_carbs=5,
        ),
        Recipe(
            recipe_id=2, name="番茄炒蛋（1人份）", category="main_dish", cuisine_type="chinese",
            prep_time=5, cook_time=5, servings=1,
            steps=[{"step": 1, "content": "番茄切块"}, {"step": 2, "content": "炒鸡蛋"}],
            total_calories=150, total_protein=10, total_fat=8, total_carbs=5,
        ),
    ]
    for r in recipes:
        db_session.add(r)

    # 关联：番茄炒蛋 = 番茄2个 + 鸡蛋3个 + 酱油1勺
    assocs = [
        RecipeIngredient(recipe_id=1, ingredient_id=1, quantity=2, unit="个"),
        RecipeIngredient(recipe_id=1, ingredient_id=2, quantity=3, unit="个"),
        RecipeIngredient(recipe_id=1, ingredient_id=8, quantity=1, unit="勺"),
        RecipeIngredient(recipe_id=2, ingredient_id=1, quantity=2, unit="个"),
        RecipeIngredient(recipe_id=2, ingredient_id=2, quantity=3, unit="个"),
    ]
    for a in assocs:
        db_session.add(a)

    db_session.commit()
    return db_session


# ═══════════════════════════════════════════════════
# 测试：单位转换
# ═══════════════════════════════════════════════════

class TestUnitConversion:
    """验证单位→克数估算正确"""

    def test_weight_units(self):
        """标准重量单位"""
        assert get_estimated_grams(1, "g") == 1.0
        assert get_estimated_grams(1, "kg") == 1000.0
        assert get_estimated_grams(1, "斤") == 500.0
        assert get_estimated_grams(1, "两") == 50.0

    def test_volume_units(self):
        """体积单位"""
        assert get_estimated_grams(1, "ml") == 1.0
        assert get_estimated_grams(1, "L") == 1000.0
        assert get_estimated_grams(1, "勺") == 15.0
        assert get_estimated_grams(1, "茶匙") == 5.0

    def test_category_adjusted_units(self):
        """按食材分类调整的单位"""
        # 蔬菜类的"个" = 150g
        assert get_estimated_grams(2, "个", "vegetable") == 300.0  # 2个番茄
        # 蛋类的"个" = 50g
        assert get_estimated_grams(3, "个", "egg") == 150.0  # 3个鸡蛋
        # 肉类默认
        assert get_estimated_grams(1, "块", "meat") == 200.0

    def test_unknown_unit_falls_back(self):
        """未知单位按 1x 处理"""
        result = get_estimated_grams(5, "unknown_unit")
        assert result == 5.0

    def test_quantity_scaling(self):
        """数量倍数正确"""
        assert get_estimated_grams(0.5, "斤") == 250.0  # 半斤
        assert get_estimated_grams(2, "两") == 100.0    # 二两


# ═══════════════════════════════════════════════════
# 测试：单菜营养计算
# ═══════════════════════════════════════════════════

class TestRecipeNutrition:
    """验证菜谱营养计算"""

    def test_calculate_tomato_egg(self, seed_data):
        """番茄炒蛋（2人份）的营养计算

        番茄 2个 × 150g = 300g
          热量: (300/100) × 18 = 54 kcal
          蛋白: (300/100) × 0.9 = 2.7 g
        鸡蛋 3个 × 50g = 150g
          热量: (150/100) × 144 = 216 kcal
          蛋白: (150/100) × 13.3 = 19.95 g
        酱油 1勺 × 15g = 15g
          热量: (15/100) × 60 = 9 kcal
        总热量 = 54 + 216 + 9 = 279 kcal
        每份(2人) = 279 / 2 ≈ 139.5 kcal
        """
        result = calculate_recipe_nutrition(seed_data, 1)
        assert result["recipe_id"] == 1
        assert result["name"] == "番茄炒蛋"
        assert result["servings"] == 2

        # 总营养（整道菜）
        total = result["total"]
        assert abs(total["calories"] - 279.0) < 1.0

        # 每份营养（÷2）
        per = result["per_serving"]
        assert abs(per["calories"] - 139.5) < 2.0
        assert per["protein"] > 0
        assert per["fat"] > 0

        # 食材明细
        assert len(result["ingredient_details"]) == 3
        assert result["ingredient_details"][0]["name"] == "番茄"
        assert result["ingredient_details"][0]["estimated_grams"] == 300.0

    def test_calculate_single_serving(self, seed_data):
        """1人份的菜谱"""
        result = calculate_recipe_nutrition(seed_data, 2)
        assert result["servings"] == 1
        # 总营养同 per_serving（因为 servings=1）
        assert abs(result["total"]["calories"] - result["per_serving"]["calories"]) < 0.1

    def test_calculate_with_custom_servings(self, seed_data):
        """自定义份数"""
        result = calculate_recipe_nutrition(seed_data, 1, servings=4)
        assert result["servings"] == 4
        # 总营养不变，每份减半
        result2 = calculate_recipe_nutrition(seed_data, 1, servings=2)
        assert abs(result["per_serving"]["calories"] * 2 - result2["per_serving"]["calories"]) < 0.1

    def test_nutrition_has_all_keys(self, seed_data):
        """营养数据包含所有5个指标"""
        result = calculate_recipe_nutrition(seed_data, 1)
        for key in ["calories", "protein", "fat", "carbs", "fiber"]:
            assert key in result["total"]
            assert key in result["per_serving"]

    def test_ingredient_details_structure(self, seed_data):
        """食材明细字段完整"""
        result = calculate_recipe_nutrition(seed_data, 1)
        detail = result["ingredient_details"][0]
        assert "ingredient_id" in detail
        assert "name" in detail
        assert "quantity" in detail
        assert "unit" in detail
        assert "estimated_grams" in detail
        assert "nutrition" in detail


# ═══════════════════════════════════════════════════
# 测试：多菜营养汇总
# ═══════════════════════════════════════════════════

class TestMealNutrition:
    """验证多道菜的营养汇总"""

    def test_meal_aggregation(self, seed_data):
        """两餐汇总"""
        meal_plan = [(1, 1), (1, 1)]  # 番茄炒蛋 x2份
        result = calculate_nutrition_for_meals(seed_data, meal_plan)

        assert len(result["meals"]) == 2
        assert result["meals"][0]["name"] == "番茄炒蛋"

        # 2份番茄炒蛋，总热量 = 单份 × 2
        single = calculate_recipe_nutrition(seed_data, 1, servings=1)
        expected_calories = single["per_serving"]["calories"] * 2
        assert abs(result["total"]["calories"] - expected_calories) < 1.0

    def test_meal_details(self, seed_data):
        """每餐明细"""
        result = calculate_nutrition_for_meals(seed_data, [(1, 1)])
        assert result["meals"][0]["recipe_id"] == 1
        assert result["meals"][0]["servings"] == 1
        assert "nutrition" in result["meals"][0]


# ═══════════════════════════════════════════════════
# 测试：边界情况
# ═══════════════════════════════════════════════════

class TestEdgeCases:
    """边界情况"""

    def test_recipe_not_found(self, db_session):
        """不存在的菜谱应报错"""
        with pytest.raises(ValueError, match="not found"):
            calculate_recipe_nutrition(db_session, 999)

    def test_recipe_without_ingredients(self, db_session):
        """没食材的菜谱返回全0"""
        r = Recipe(
            recipe_id=99, name="空菜谱", category="main_dish", cuisine_type="chinese",
            prep_time=5, cook_time=5, servings=1,
            steps=[{"step": 1, "content": "无"}],
        )
        db_session.add(r)
        db_session.commit()

        result = calculate_recipe_nutrition(db_session, 99)
        assert result["total"]["calories"] == 0.0
        assert result["total"]["protein"] == 0.0
        assert len(result["ingredient_details"]) == 0

    def test_ingredient_without_nutrition(self, db_session, seed_data):
        """没有营养数据的食材，计算时应跳过"""
        # 添加一个没有 nutrition 记录的食材
        ing = Ingredient(ingredient_id=99, name="未知食材", category="other", unit="g")
        db_session.add(ing)
        assoc = RecipeIngredient(recipe_id=1, ingredient_id=99, quantity=100, unit="g")
        db_session.add(assoc)
        db_session.commit()

        result = calculate_recipe_nutrition(db_session, 1)
        # 营养数据不应受未知食材影响
        assert len(result["ingredient_details"]) == 3  # 只包含有营养数据的食材
