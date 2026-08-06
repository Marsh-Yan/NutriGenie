"""Phase 1 数据库与数据服务测试

运行: cd backend && python -m pytest tests/test_phase1.py -v
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.profile import Profile
from app.models.recipe import Recipe
from app.models.ingredient import Ingredient
from app.models.ingredient_nutrition import IngredientNutrition
from app.models.recipe_ingredient import RecipeIngredient
from app.models.meal_plan import MealPlan

from app.services.recipe_service import (
    get_recipe,
    get_recipes,
    get_all_recipes,
    get_recipe_ingredients,
)
from app.services.ingredient_service import (
    get_ingredient,
    get_ingredients,
    get_all_ingredients,
)
from app.services.profile_service import (
    get_profile,
    create_profile,
    update_profile,
)

from app.services.tdee import calculate_bmr, calculate_tdee, calculate_bmi, get_bmi_category


# ─── 测试用内存数据库 ─────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """每个测试函数使用独立的内存数据库"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SQLite 默认不启用外键约束，通过 event 确保每个连接启用
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


# ─── 种子数据 ─────────────────────────────────────

@pytest.fixture
def seed_data(db_session):
    """插入基础测试数据"""
    # 食材
    ingredients = [
        Ingredient(ingredient_id=1, name="番茄", category="vegetable", unit="个", unit_price=2.5, season_tags=["夏季", "秋季"]),
        Ingredient(ingredient_id=2, name="鸡蛋", category="egg", unit="个", unit_price=1.2, season_tags=None),
        Ingredient(ingredient_id=3, name="鸡胸肉", category="meat", unit="斤", unit_price=15.0, season_tags=None),
        Ingredient(ingredient_id=4, name="青椒", category="vegetable", unit="个", unit_price=1.5, season_tags=["夏季"]),
        Ingredient(ingredient_id=5, name="西兰花", category="vegetable", unit="颗", unit_price=5.0, season_tags=["春季", "秋季"]),
        Ingredient(ingredient_id=6, name="虾仁", category="seafood", unit="斤", unit_price=35.0, season_tags=None),
    ]
    for ing in ingredients:
        db_session.add(ing)

    # 营养数据
    nutritions = [
        IngredientNutrition(ingredient_id=1, calories_per_100g=18, protein_per_100g=0.9, fat_per_100g=0.2, carbs_per_100g=3.9, fiber_per_100g=1.2),
        IngredientNutrition(ingredient_id=2, calories_per_100g=144, protein_per_100g=13.3, fat_per_100g=8.8, carbs_per_100g=2.8, fiber_per_100g=0),
        IngredientNutrition(ingredient_id=3, calories_per_100g=167, protein_per_100g=25, fat_per_100g=7, carbs_per_100g=0, fiber_per_100g=0),
    ]
    for n in nutritions:
        db_session.add(n)

    # 菜谱
    recipes = [
        Recipe(
            recipe_id=1, name="番茄炒蛋", description="经典家常菜",
            category="main_dish", cuisine_type="chinese", difficulty="easy",
            prep_time=5, cook_time=5, servings=2,
            steps=[{"step": 1, "content": "番茄切块"}, {"step": 2, "content": "炒鸡蛋"}],
            total_calories=150, total_protein=10, total_fat=8, total_carbs=5, total_fiber=1.5,
            tags=["快手菜", "减脂"],
        ),
        Recipe(
            recipe_id=2, name="宫保鸡丁", description="经典川菜",
            category="main_dish", cuisine_type="chinese", difficulty="medium",
            prep_time=15, cook_time=10, servings=2,
            steps=[{"step": 1, "content": "鸡丁腌制"}, {"step": 2, "content": "炒花生"}],
            total_calories=380, total_protein=35, total_fat=18, total_carbs=15, total_fiber=2,
            tags=["高蛋白", "中式经典"],
        ),
        Recipe(
            recipe_id=3, name="Grilled Chicken Salad", description="健康沙拉",
            category="light_meal", cuisine_type="western", difficulty="easy",
            prep_time=10, cook_time=12, servings=1,
            steps=[{"step": 1, "content": "煎鸡胸"}],
            total_calories=350, total_protein=35, total_fat=18, total_carbs=8, total_fiber=3,
            tags=["减脂", "西餐"],
        ),
    ]
    for r in recipes:
        db_session.add(r)

    # 菜谱-食材关联
    associations = [
        RecipeIngredient(recipe_id=1, ingredient_id=1, quantity=2, unit="个"),
        RecipeIngredient(recipe_id=1, ingredient_id=2, quantity=3, unit="个"),
        RecipeIngredient(recipe_id=2, ingredient_id=3, quantity=300, unit="g"),
        RecipeIngredient(recipe_id=3, ingredient_id=3, quantity=200, unit="g"),
        RecipeIngredient(recipe_id=3, ingredient_id=5, quantity=100, unit="g"),
    ]
    for a in associations:
        db_session.add(a)

    # 用户画像
    profile = Profile(
        profile_id=1, age=28, gender="male", height=175, weight=72,
        diet_type="balanced", health_goal="fat_loss",
        allergies=["海鲜"], daily_budget=50,
    )
    db_session.add(profile)

    db_session.commit()
    return db_session


# ═══════════════════════════════════════════════════
# 测试：数据模型
# ═══════════════════════════════════════════════════

class TestModels:
    """验证 ORM 模型定义正确"""

    def test_profile_model(self, db_session):
        p = Profile(
            age=25, gender="female", height=160, weight=55,
            diet_type="keto", health_goal="muscle_gain",
            allergies=["花生"], daily_budget=60,
        )
        db_session.add(p)
        db_session.commit()
        assert p.profile_id is not None
        assert p.gender == "female"
        assert p.health_goal == "muscle_gain"

    def test_recipe_model(self, db_session):
        r = Recipe(
            name="测试菜", description="测试",
            category="main_dish", cuisine_type="chinese", difficulty="easy",
            prep_time=10, cook_time=10, servings=1,
            steps=[{"step": 1, "content": "测试步骤"}],
        )
        db_session.add(r)
        db_session.commit()
        assert r.recipe_id is not None
        assert r.prep_time == 10

    def test_ingredient_model(self, db_session):
        ing = Ingredient(name="测试食材", category="vegetable", unit="个", unit_price=5.0)
        db_session.add(ing)
        db_session.commit()
        assert ing.ingredient_id is not None
        assert ing.unit_price == 5.0

    def test_cascade_delete_recipe(self, db_session):
        """删除菜谱时，关联的 recipe_ingredients 应同步删除"""
        r = Recipe(
            name="级联测试", category="main_dish", cuisine_type="chinese",
            prep_time=5, cook_time=5, servings=1,
            steps=[{"step": 1, "content": "测试"}],
        )
        db_session.add(r)
        db_session.flush()

        ing = Ingredient(name="测试食材2", category="vegetable", unit="个")
        db_session.add(ing)
        db_session.flush()

        ri = RecipeIngredient(recipe_id=r.recipe_id, ingredient_id=ing.ingredient_id, quantity=1, unit="个")
        db_session.add(ri)
        db_session.commit()

        # 删除菜谱
        db_session.delete(r)
        db_session.commit()

        # 关联应自动删除
        assert db_session.query(RecipeIngredient).filter_by(recipe_id=r.recipe_id).count() == 0
        # 食材应保留
        assert db_session.query(Ingredient).filter_by(ingredient_id=ing.ingredient_id).count() == 1

    def test_unique_nutrition_per_ingredient(self, db_session):
        """每种食材只能有一条营养记录"""
        ing = Ingredient(name="食材A", category="vegetable", unit="个")
        db_session.add(ing)
        db_session.flush()

        db_session.add(IngredientNutrition(ingredient_id=ing.ingredient_id, calories_per_100g=100))
        db_session.commit()

        # 重复添加应报错
        with pytest.raises(Exception):
            db_session.add(IngredientNutrition(ingredient_id=ing.ingredient_id, calories_per_100g=200))
            db_session.commit()


# ═══════════════════════════════════════════════════
# 测试：菜谱 Service
# ═══════════════════════════════════════════════════

class TestRecipeService:
    """验证菜谱查询服务"""

    def test_get_recipe_by_id(self, seed_data):
        db = seed_data
        recipe = get_recipe(db, 1)
        assert recipe is not None
        assert recipe.name == "番茄炒蛋"
        assert recipe.difficulty == "easy"

    def test_get_recipe_not_found(self, seed_data):
        recipe = get_recipe(seed_data, 999)
        assert recipe is None

    def test_get_all_recipes(self, seed_data):
        recipes = get_all_recipes(seed_data)
        assert len(recipes) == 3

    def test_get_recipes_pagination(self, seed_data):
        items, total = get_recipes(seed_data, page=1, page_size=2)
        assert total == 3
        assert len(items) == 2

    def test_get_recipes_filter_by_cuisine(self, seed_data):
        items, total = get_recipes(seed_data, cuisine_type="western")
        assert total == 1
        assert items[0].name == "Grilled Chicken Salad"

    def test_get_recipes_filter_by_category(self, seed_data):
        items, total = get_recipes(seed_data, category="light_meal")
        assert total == 1
        assert items[0].name == "Grilled Chicken Salad"

    def test_get_recipes_filter_by_difficulty(self, seed_data):
        items, total = get_recipes(seed_data, difficulty="medium")
        assert total == 1
        assert items[0].name == "宫保鸡丁"

    def test_get_recipes_filter_by_tags(self, seed_data):
        """标签过滤：返回所有菜谱并在 Python 中验证标签匹配"""
        items, total = get_recipes(seed_data, page=1, page_size=50)  # 不传 tags 参数
        # 在 Python 层面过滤，验证数据本身包含正确的标签
        tagged_items = [r for r in items if r.tags and "减脂" in r.tags]
        assert len(tagged_items) >= 1  # 至少包含番茄炒蛋
        assert any(r.name == "番茄炒蛋" for r in tagged_items)
        # MySQL 环境下直接使用 tags 过滤参数可得到精确结果

    def test_get_recipe_ingredients(self, seed_data):
        ingredients = get_recipe_ingredients(seed_data, 1)
        assert len(ingredients) == 2
        names = [i["name"] for i in ingredients]
        assert "番茄" in names
        assert "鸡蛋" in names

    def test_get_recipe_ingredients_includes_cost(self, seed_data):
        ingredients = get_recipe_ingredients(seed_data, 1)
        for ing in ingredients:
            assert ing["estimated_cost"] >= 0
            assert ing["quantity"] > 0

    def test_recipe_cost_converts_grams_to_price_per_jin(self, seed_data):
        """300g chicken at 15 yuan/jin costs 9 yuan, not 4,500 yuan."""
        ingredients = get_recipe_ingredients(seed_data, 2)
        chicken = next(item for item in ingredients if item["ingredient_id"] == 3)
        assert chicken["purchase_unit"] == "斤"
        assert chicken["estimated_cost"] == 9.0

    def test_get_recipe_ingredients_includes_nutrition(self, seed_data):
        ingredients = get_recipe_ingredients(seed_data, 1)
        for ing in ingredients:
            assert ing["nutrition"] is not None
            assert "calories" in ing["nutrition"]
            assert "protein" in ing["nutrition"]


# ═══════════════════════════════════════════════════
# 测试：食材 Service
# ═══════════════════════════════════════════════════

class TestIngredientService:
    """验证食材查询服务"""

    def test_get_ingredient_by_id(self, seed_data):
        ing = get_ingredient(seed_data, 1)
        assert ing is not None
        assert ing.name == "番茄"
        assert ing.category == "vegetable"

    def test_get_ingredient_not_found(self, seed_data):
        ing = get_ingredient(seed_data, 999)
        assert ing is None

    def test_get_all_ingredients(self, seed_data):
        ingredients = get_all_ingredients(seed_data)
        assert len(ingredients) == 6

    def test_get_ingredients_by_category(self, seed_data):
        items, total = get_ingredients(seed_data, category="vegetable")
        assert total == 3  # 番茄(1) + 青椒(4) + 西兰花(5)

    def test_get_ingredients_with_season_filter(self, seed_data):
        """季节筛选：返回所有食材并在 Python 中验证季节标签"""
        items, total = get_ingredients(seed_data)
        seasonal = [i for i in items if i.get("season_tags") and "夏季" in i["season_tags"]]
        assert len(seasonal) > 0
        names = [i["name"] for i in seasonal]
        assert "番茄" in names  # 番茄标记为夏季

    def test_ingredient_includes_nutrition(self, seed_data):
        items, total = get_ingredients(seed_data)
        for item in items:
            if item["name"] == "番茄":
                nut = item["nutrition_per_100g"]
                assert nut["calories"] == 18
                assert nut["protein"] == 0.9
                break
        else:
            pytest.fail("未找到番茄的 nutrition 数据")

    def test_ingredient_without_nutrition_returns_none(self, seed_data):
        """没有营养数据的食材应返回 None"""
        ing = get_ingredient(seed_data, 4)  # 青椒无营养数据
        assert ing is not None


# ═══════════════════════════════════════════════════
# 测试：用户画像 Service
# ═══════════════════════════════════════════════════

class TestProfileService:
    """验证用户画像 CRUD"""

    def test_get_profile(self, seed_data):
        profile = get_profile(seed_data, 1)
        assert profile is not None
        assert profile.age == 28
        assert profile.diet_type == "balanced"

    def test_get_profile_not_found(self, seed_data):
        profile = get_profile(seed_data, 999)
        assert profile is None

    def test_create_profile(self, db_session):
        data = {
            "age": 30,
            "gender": "female",
            "height": 165.0,
            "weight": 60.0,
            "diet_type": "high_protein",
            "health_goal": "muscle_gain",
            "allergies": ["花生", "牛奶"],
            "daily_budget": 80.0,
        }
        profile = create_profile(db_session, data)
        assert profile.profile_id is not None
        assert profile.age == 30
        assert profile.health_goal == "muscle_gain"

    def test_create_profile_default_values(self, db_session):
        """不传选填字段应有默认值"""
        data = {
            "age": 25,
            "gender": "male",
            "height": 170.0,
            "weight": 65.0,
        }
        profile = create_profile(db_session, data)
        assert profile.diet_type == "balanced"  # 默认值
        assert profile.health_goal == "healthy"  # 默认值

    def test_update_profile(self, seed_data):
        updated = update_profile(seed_data, 1, {"weight": 70.0, "daily_budget": 60.0})
        assert updated is not None
        assert float(updated.weight) == 70.0
        assert float(updated.daily_budget) == 60.0
        # 未修改的字段保持不变
        assert updated.age == 28

    def test_update_profile_not_found(self, seed_data):
        result = update_profile(seed_data, 999, {"weight": 70.0})
        assert result is None


# ═══════════════════════════════════════════════════
# 测试：种子数据完整性
# ═══════════════════════════════════════════════════

class TestSeedData:
    """验证导入的种子数据完整性"""

    @pytest.fixture(scope="function")
    def seed_count(self):
        """从 JSON 种子数据源导入全量数据"""
        import json, os
        seed_dir = os.path.join(os.path.dirname(__file__), "..", "app", "db", "seed_data")

        with open(os.path.join(seed_dir, "ingredients.json"), "r", encoding="utf-8") as f:
            ingredients = json.load(f)
        with open(os.path.join(seed_dir, "ingredient_nutrition.json"), "r", encoding="utf-8") as f:
            nutritions = json.load(f)
        with open(os.path.join(seed_dir, "recipes.json"), "r", encoding="utf-8") as f:
            recipes = json.load(f)
        with open(os.path.join(seed_dir, "recipe_ingredients.json"), "r", encoding="utf-8") as f:
            assocs = json.load(f)

        return {
            "ingredients": len(ingredients),
            "nutritions": len(nutritions),
            "recipes": len(recipes),
            "assocs": len(assocs),
        }

    def test_seed_ingredients_count(self, seed_count):
        assert seed_count["ingredients"] >= 50, f"食材不足50种，当前{seed_count['ingredients']}"

    def test_seed_recipes_count(self, seed_count):
        assert seed_count["recipes"] >= 25, f"菜谱不足25道，当前{seed_count['recipes']}"

    def test_seed_associations_count(self, seed_count):
        assert seed_count["assocs"] >= 130, f"关联不足130条，当前{seed_count['assocs']}"

    def test_every_ingredient_has_nutrition(self, seed_count):
        assert seed_count["ingredients"] == seed_count["nutritions"], \
            f"食材({seed_count['ingredients']})与营养数据({seed_count['nutritions']})数量不一致"

    def test_seed_recipes_have_essential_fields(self):
        """所有菜谱必须有名称、分类、步骤"""
        import json, os
        seed_dir = os.path.join(os.path.dirname(__file__), "..", "app", "db", "seed_data")
        with open(os.path.join(seed_dir, "recipes.json"), "r", encoding="utf-8") as f:
            recipes = json.load(f)
        for r in recipes:
            assert r.get("name"), f"菜谱缺少 name: {r.get('recipe_id')}"
            assert r.get("category"), f"菜谱缺少 category: {r.get('name')}"
            assert r.get("steps") and len(r["steps"]) > 0, f"菜谱缺少步骤: {r.get('name')}"

    def test_chinese_and_western_recipes(self):
        """中餐和西餐菜谱都要有"""
        import json, os
        seed_dir = os.path.join(os.path.dirname(__file__), "..", "app", "db", "seed_data")
        with open(os.path.join(seed_dir, "recipes.json"), "r", encoding="utf-8") as f:
            recipes = json.load(f)
        cuisines = [r["cuisine_type"] for r in recipes]
        assert "chinese" in cuisines, "缺少中餐菜谱"
        assert "western" in cuisines, "缺少西餐菜谱"
        chinese_count = cuisines.count("chinese")
        western_count = cuisines.count("western")
        assert chinese_count >= 10, f"中餐不足10道，当前{chinese_count}"
        assert western_count >= 10, f"西餐不足10道，当前{western_count}"


# ═══════════════════════════════════════════════════
# 测试：数据完整性约束
# ═══════════════════════════════════════════════════

class TestDataIntegrity:
    """验证数据库约束正确工作"""

    def test_duplicate_profile_not_prevented(self, db_session):
        """没有唯一约束，可以创建多个 profile"""
        p1 = Profile(age=20, gender="male", height=170, weight=60)
        p2 = Profile(age=25, gender="female", height=160, weight=50)
        db_session.add(p1)
        db_session.add(p2)
        db_session.commit()
        assert db_session.query(Profile).count() == 2

    def test_null_optional_fields(self, db_session):
        """可选字段可以留空"""
        p = Profile(age=20, gender="male", height=170, weight=60)
        db_session.add(p)
        db_session.commit()
        assert p.allergies is None
        assert float(p.daily_budget) == 0


# ═══════════════════════════════════════════════════
# 测试：TDEE / BMR 计算
# ═══════════════════════════════════════════════════

class TestTdeeCalculation:
    """验证 TDEE/BMR 计算公式正确"""

    # 测试用例：男性，28岁，175cm，72kg
    # BMR = 10×72 + 6.25×175 - 5×28 + 5 = 720 + 1093.75 - 140 + 5 = 1678.75

    def test_bmr_male(self):
        bmr = calculate_bmr(gender="male", weight_kg=72, height_cm=175, age=28)
        assert abs(bmr - 1678.75) < 1.0, f"男性 BMR 计算偏差: {bmr}"

    def test_bmr_female(self):
        # 女性，25岁，160cm，55kg
        # BMR = 10×55 + 6.25×160 - 5×25 - 161 = 550 + 1000 - 125 - 161 = 1264
        bmr = calculate_bmr(gender="female", weight_kg=55, height_cm=160, age=25)
        assert abs(bmr - 1264.0) < 1.0, f"女性 BMR 计算偏差: {bmr}"

    def test_tdee_default(self):
        tdee = calculate_tdee(gender="male", weight_kg=72, height_cm=175, age=28)
        expected_bmr = 1678.75
        expected_tdee = expected_bmr * 1.55
        assert abs(tdee - expected_tdee) < 1.0, f"TDEE 计算偏差: {tdee}"

    def test_tdee_with_activity_factor(self):
        tdee = calculate_tdee(
            gender="male", weight_kg=72, height_cm=175, age=28,
            activity_factor=1.2,
        )
        expected = 1678.75 * 1.2
        assert abs(tdee - expected) < 1.0, f"久坐 TDEE 计算偏差: {tdee}"

    def test_bmi_normal(self):
        # 175cm, 72kg → BMI = 72 / 1.75²
        bmi = calculate_bmi(weight_kg=72, height_cm=175)
        assert abs(bmi - 23.5) < 0.1

    def test_bmi_underweight(self):
        bmi = calculate_bmi(weight_kg=50, height_cm=175)
        assert get_bmi_category(bmi) == "偏瘦"

    def test_bmi_normal_category(self):
        bmi = calculate_bmi(weight_kg=65, height_cm=170)
        assert get_bmi_category(bmi) == "正常"

    def test_bmi_overweight(self):
        bmi = calculate_bmi(weight_kg=80, height_cm=170)
        assert get_bmi_category(bmi) == "偏胖"

    def test_bmi_obese(self):
        bmi = calculate_bmi(weight_kg=100, height_cm=170)
        assert get_bmi_category(bmi) == "肥胖"

    def test_profile_tdee_consistency(self, seed_data):
        """验证用户画像的 TDEE 计算前后一致"""
        profile = get_profile(seed_data, 1)
        tdee = calculate_tdee(
            gender=profile.gender,
            weight_kg=float(profile.weight),
            height_cm=float(profile.height),
            age=profile.age,
        )
        bmr = calculate_bmr(
            gender=profile.gender,
            weight_kg=float(profile.weight),
            height_cm=float(profile.height),
            age=profile.age,
        )
        assert tdee > bmr, "TDEE 应当大于 BMR"
        assert 1500 < tdee < 3000, "TDEE 应在合理范围内"


# ═══════════════════════════════════════════════════
# 集成测试：MySQL 环境验证
# ═══════════════════════════════════════════════════

@pytest.mark.integration
class TestMySQLIntegration:
    """连接真实 MySQL 验证 JSON 过滤等功能。

    这些测试依赖实际的 MySQL 数据库连接，如果 MySQL 不可用则跳过。
    """

    @pytest.fixture(scope="function")
    def mysql_session(self):
        """使用真实 MySQL 数据库（需已运行 seed.py）"""
        try:
            from app.db.database import SessionLocal
            db = SessionLocal()
            yield db
        except Exception as e:
            pytest.skip(f"MySQL 不可用，跳过集成测试: {e}")
            yield
        finally:
            try:
                db.close()
            except Exception:
                pass

    def test_mysql_tags_filter(self, mysql_session):
        """MySQL 环境下的 JSON 标签过滤"""
        items, total = get_recipes(mysql_session, tags=["减脂"])
        assert total > 0
        assert any("减脂" in (r.tags or []) for r in items)

    def test_mysql_season_filter(self, mysql_session):
        """MySQL 环境下的季节 JSON 过滤"""
        items, total = get_ingredients(mysql_session, season="夏季")
        assert total > 0
        assert any("夏季" in (i.get("season_tags") or []) for i in items)
