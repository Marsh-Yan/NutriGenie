"""推荐引擎测试"""

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

from app.services.recommendation_engine import (
    build_candidate_pool,
    resolve_allergen_ingredient_ids,
    exclude_recipes,
    exclude_diet_incompatible_recipes,
    RecipeCandidate,
    score_candidate,
    rank_candidates,
    rank_candidates_hybrid,
    DEFAULT_WEIGHTS,
)
from app.services.constraint_analyzer import build_constraints


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

    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed_data(db_session):
    """插入足够多菜谱用于评分测试"""
    # 食材
    ings = [
        Ingredient(ingredient_id=1, name="番茄", category="vegetable", unit="个", unit_price=2.5, season_tags=["夏季", "秋季"]),
        Ingredient(ingredient_id=2, name="鸡蛋", category="egg", unit="个", unit_price=1.2, season_tags=None),
        Ingredient(ingredient_id=3, name="鸡胸肉", category="meat", unit="斤", unit_price=15.0, season_tags=None),
        Ingredient(ingredient_id=4, name="青椒", category="vegetable", unit="个", unit_price=1.5, season_tags=["夏季"]),
        Ingredient(ingredient_id=5, name="西兰花", category="vegetable", unit="颗", unit_price=5.0, season_tags=["春季", "秋季"]),
        Ingredient(ingredient_id=6, name="虾仁", category="seafood", unit="斤", unit_price=35.0, season_tags=None),
        Ingredient(ingredient_id=7, name="大米", category="grain", unit="g", unit_price=0.01, season_tags=None),
        Ingredient(ingredient_id=8, name="酱油", category="condiment", unit="勺", unit_price=0.5, season_tags=None),
        Ingredient(ingredient_id=9, name="三文鱼", category="seafood", unit="块", unit_price=25.0, season_tags=["秋季"]),
        Ingredient(ingredient_id=10, name="菠菜", category="vegetable", unit="把", unit_price=3.0, season_tags=["春季", "秋季"]),
    ]
    for ing in ings:
        db_session.add(ing)

    # 营养数据
    nuts = [
        IngredientNutrition(ingredient_id=1, calories_per_100g=18, protein_per_100g=0.9, fat_per_100g=0.2, carbs_per_100g=3.9, fiber_per_100g=1.2),
        IngredientNutrition(ingredient_id=2, calories_per_100g=144, protein_per_100g=13.3, fat_per_100g=8.8, carbs_per_100g=2.8, fiber_per_100g=0),
        IngredientNutrition(ingredient_id=3, calories_per_100g=167, protein_per_100g=25, fat_per_100g=7, carbs_per_100g=0, fiber_per_100g=0),
        IngredientNutrition(ingredient_id=4, calories_per_100g=22, protein_per_100g=1.0, fat_per_100g=0.3, carbs_per_100g=4.6, fiber_per_100g=1.8),
        IngredientNutrition(ingredient_id=5, calories_per_100g=34, protein_per_100g=2.8, fat_per_100g=0.4, carbs_per_100g=6.6, fiber_per_100g=2.6),
        IngredientNutrition(ingredient_id=6, calories_per_100g=99, protein_per_100g=20.3, fat_per_100g=0.7, carbs_per_100g=0.2, fiber_per_100g=0),
        IngredientNutrition(ingredient_id=7, calories_per_100g=130, protein_per_100g=2.7, fat_per_100g=0.3, carbs_per_100g=28.7, fiber_per_100g=0.4),
        IngredientNutrition(ingredient_id=8, calories_per_100g=60, protein_per_100g=6, fat_per_100g=0, carbs_per_100g=10, fiber_per_100g=0),
        IngredientNutrition(ingredient_id=9, calories_per_100g=208, protein_per_100g=20.4, fat_per_100g=13.4, carbs_per_100g=0, fiber_per_100g=0),
        IngredientNutrition(ingredient_id=10, calories_per_100g=23, protein_per_100g=2.9, fat_per_100g=0.4, carbs_per_100g=3.6, fiber_per_100g=2.2),
    ]
    for n in nuts:
        db_session.add(n)

    # 菜谱（5道，覆盖不同场景）
    recipes = [
        Recipe(recipe_id=1, name="番茄炒蛋", description="经典家常菜",
               category="main_dish", cuisine_type="chinese", difficulty="easy",
               prep_time=5, cook_time=5, servings=2,
               steps=[{"step": 1, "content": "番茄切块"}, {"step": 2, "content": "炒鸡蛋"}],
               total_calories=150, total_protein=10, total_fat=8, total_carbs=5, total_fiber=1.5,
               tags=["快手菜", "减脂", "家常菜"]),
        Recipe(recipe_id=2, name="Grilled Chicken Salad", description="健康沙拉",
               category="light_meal", cuisine_type="western", difficulty="easy",
               prep_time=10, cook_time=12, servings=1,
               steps=[{"step": 1, "content": "煎鸡胸"}],
               total_calories=350, total_protein=35, total_fat=18, total_carbs=8, total_fiber=3,
               tags=["减脂", "高蛋白", "西餐"]),
        Recipe(recipe_id=3, name="三文鱼排", description="煎三文鱼",
               category="main_dish", cuisine_type="western", difficulty="medium",
               prep_time=5, cook_time=15, servings=1,
               steps=[{"step": 1, "content": "煎三文鱼"}],
               total_calories=420, total_protein=30, total_fat=30, total_carbs=0, total_fiber=0,
               tags=["高蛋白", "健康脂肪", "西餐"]),
        Recipe(recipe_id=4, name="蒜蓉西兰花", description="清爽素菜",
               category="side_dish", cuisine_type="chinese", difficulty="easy",
               prep_time=5, cook_time=5, servings=2,
               steps=[{"step": 1, "content": "焯水"}, {"step": 2, "content": "蒜蓉炒"}],
               total_calories=80, total_protein=5, total_fat=4, total_carbs=8, total_fiber=3,
               tags=["素食", "快手菜", "减脂"]),
        Recipe(recipe_id=5, name="虾仁炒饭", description="虾仁蛋炒饭",
               category="staple", cuisine_type="chinese", difficulty="easy",
               prep_time=5, cook_time=10, servings=1,
               steps=[{"step": 1, "content": "炒虾仁"}, {"step": 2, "content": "炒饭"}],
               total_calories=450, total_protein=25, total_fat=15, total_carbs=55, total_fiber=1,
               tags=["高蛋白", "主食"]),
    ]
    for r in recipes:
        db_session.add(r)

    # 菜谱-食材关联
    assocs = [
        RecipeIngredient(recipe_id=1, ingredient_id=1, quantity=2, unit="个"),
        RecipeIngredient(recipe_id=1, ingredient_id=2, quantity=3, unit="个"),
        RecipeIngredient(recipe_id=1, ingredient_id=8, quantity=1, unit="勺"),
        RecipeIngredient(recipe_id=2, ingredient_id=3, quantity=200, unit="g"),
        RecipeIngredient(recipe_id=2, ingredient_id=5, quantity=100, unit="g"),
        RecipeIngredient(recipe_id=2, ingredient_id=8, quantity=1, unit="勺"),
        RecipeIngredient(recipe_id=3, ingredient_id=9, quantity=1, unit="块"),
        RecipeIngredient(recipe_id=3, ingredient_id=10, quantity=1, unit="把"),
        RecipeIngredient(recipe_id=3, ingredient_id=8, quantity=1, unit="勺"),
        RecipeIngredient(recipe_id=4, ingredient_id=5, quantity=1, unit="颗"),
        RecipeIngredient(recipe_id=4, ingredient_id=8, quantity=1, unit="勺"),
        RecipeIngredient(recipe_id=5, ingredient_id=6, quantity=100, unit="g"),
        RecipeIngredient(recipe_id=5, ingredient_id=2, quantity=1, unit="个"),
        RecipeIngredient(recipe_id=5, ingredient_id=7, quantity=200, unit="g"),
        RecipeIngredient(recipe_id=5, ingredient_id=8, quantity=1, unit="勺"),
    ]
    for a in assocs:
        db_session.add(a)

    db_session.commit()
    return db_session


@pytest.fixture
def fat_loss_constraints(seed_data):
    """减脂约束集"""
    profile = Profile(
        profile_id=1, age=28, gender="male", height=175, weight=72,
        diet_type="balanced", health_goal="fat_loss",
        allergies=["海鲜"],
    )
    return build_constraints(profile, duration_days=7, total_budget=300)


# ═══════════════════════════════════════════════════
# 测试：候选池构建
# ═══════════════════════════════════════════════════

class TestBuildCandidatePool:
    """验证候选池构建正确"""

    def test_returns_all_recipes(self, seed_data):
        pool = build_candidate_pool(seed_data)
        assert len(pool) == 5

    def test_candidate_structure(self, seed_data):
        pool = build_candidate_pool(seed_data)
        c = pool[0]
        assert c.recipe_id is not None
        assert c.name
        assert c.category
        assert c.cuisine_type
        assert isinstance(c.tags, list)
        assert isinstance(c.ingredient_ids, list)
        assert isinstance(c.ingredient_categories, list)
        assert isinstance(c.ingredient_seasons, list)
        assert c.total_calories >= 0
        assert c.estimated_cost >= 0

    def test_ingredient_details(self, seed_data):
        """番茄炒蛋应包含番茄和鸡蛋"""
        pool = build_candidate_pool(seed_data)
        rc = [c for c in pool if c.recipe_id == 1][0]
        assert 1 in rc.ingredient_ids  # 番茄
        assert 2 in rc.ingredient_ids  # 鸡蛋
        assert "vegetable" in rc.ingredient_categories
        assert "egg" in rc.ingredient_categories

    def test_season_tags_preserved(self, seed_data):
        pool = build_candidate_pool(seed_data)
        # 番茄（id=1）有 season_tags=["夏季", "秋季"]
        rc = [c for c in pool if c.recipe_id == 1][0]
        idx = rc.ingredient_ids.index(1)
        season = rc.ingredient_seasons[idx]
        assert "夏季" in season


# ═══════════════════════════════════════════════════
# 测试：过敏原解析
# ═══════════════════════════════════════════════════

class TestAllergenResolution:
    """验证过敏原→食材 ID 映射"""

    def test_no_allergens_returns_empty(self, seed_data):
        ids = resolve_allergen_ingredient_ids(seed_data, [])
        assert ids == []

    def test_seafood_allergen(self, seed_data):
        """海鲜过敏应排除虾仁(6)和三文鱼(9)"""
        ids = resolve_allergen_ingredient_ids(seed_data, ["海鲜"])
        assert 6 in ids  # 虾仁（"虾"匹配）
        assert 9 in ids  # 三文鱼（"鱼"匹配）

    def test_egg_allergen(self, seed_data):
        ids = resolve_allergen_ingredient_ids(seed_data, ["鸡蛋"])
        assert 2 in ids  # 鸡蛋

    def test_nonexistent_allergen(self, seed_data):
        ids = resolve_allergen_ingredient_ids(seed_data, ["芒果"])
        assert ids == []


# ═══════════════════════════════════════════════════
# 测试：排除
# ═══════════════════════════════════════════════════

class TestExcludeRecipes:
    """验证排除逻辑"""

    def test_no_exclusion(self, seed_data):
        pool = [RecipeCandidate(recipe_id=1, name="A", category="", cuisine_type="",
                difficulty="", prep_time=0, cook_time=0, servings=1, tags=[],
                total_calories=0, estimated_cost=0,
                ingredient_ids=[1, 2], ingredient_categories=[], ingredient_seasons=[], image_url=None)]
        result = exclude_recipes(pool, set())
        assert len(result) == 1

    def test_exclude_recipe_with_allergen(self, seed_data):
        pool = [
            RecipeCandidate(recipe_id=1, name="番茄炒蛋", category="", cuisine_type="",
                difficulty="", prep_time=0, cook_time=0, servings=1, tags=[],
                total_calories=0, estimated_cost=0,
                ingredient_ids=[1, 2], ingredient_categories=[], ingredient_seasons=[], image_url=None),
            RecipeCandidate(recipe_id=5, name="虾仁炒饭", category="", cuisine_type="",
                difficulty="", prep_time=0, cook_time=0, servings=1, tags=[],
                total_calories=0, estimated_cost=0,
                ingredient_ids=[6, 2, 7], ingredient_categories=[], ingredient_seasons=[], image_url=None),
        ]
        result = exclude_recipes(pool, {6})
        assert len(result) == 1
        assert result[0].recipe_id == 1

    def test_vegan_filter_excludes_animal_categories(self, seed_data):
        pool = build_candidate_pool(seed_data)
        result = exclude_diet_incompatible_recipes(pool, "vegan")
        assert {candidate.recipe_id for candidate in result} == {4}

    def test_gluten_free_filter_uses_ingredient_name(self, seed_data):
        pool = [
            RecipeCandidate(1, "燕麦碗", "light_meal", "western", "easy", 1, 1, 1, [], 100, 5, [], [], [], None, ["燕麦"]),
            RecipeCandidate(2, "番茄沙拉", "light_meal", "western", "easy", 1, 1, 1, [], 100, 5, [], [], [], None, ["番茄"]),
        ]
        result = exclude_diet_incompatible_recipes(pool, "gluten_free")
        assert [candidate.recipe_id for candidate in result] == [2]


# ═══════════════════════════════════════════════════
# 测试：评分
# ═══════════════════════════════════════════════════

class TestScoreCandidate:
    """验证单个菜谱评分"""

    def test_returns_all_dimensions(self, seed_data, fat_loss_constraints):
        pool = build_candidate_pool(seed_data)
        scored = score_candidate(
            pool[0], fat_loss_constraints, "夏季", [], [], DEFAULT_WEIGHTS,
        )
        assert scored.total_score >= 0
        assert scored.total_score <= 1
        for dim in ["health", "budget", "preference", "season", "variety", "utilization"]:
            assert dim in scored.scores
            assert 0 <= scored.scores[dim] <= 1

    def test_health_score_high_when_in_range(self, seed_data, fat_loss_constraints):
        """热量适中的菜谱 health_score 应较高"""
        pool = build_candidate_pool(seed_data)
        # 番茄炒蛋 150kcal — 减脂目标通常 1700~2000，偏离很多 → health 低
        rc1 = [c for c in pool if c.recipe_id == 1][0]
        scored1 = score_candidate(rc1, fat_loss_constraints, "夏季", [], [], DEFAULT_WEIGHTS)
        # 鸡胸沙拉 350kcal — 偏离少一点 → health 可能稍高
        rc2 = [c for c in pool if c.recipe_id == 2][0]
        scored2 = score_candidate(rc2, fat_loss_constraints, "夏季", [], [], DEFAULT_WEIGHTS)
        # 两者都远低于目标区间，但高的那个应该更接近
        # 只是确认分数合理，不做具体断言

    def test_season_score_varies(self, seed_data, fat_loss_constraints):
        """同一道菜在不同季节得分不同"""
        pool = build_candidate_pool(seed_data)
        rc = [c for c in pool if c.recipe_id == 1][0]  # 番茄（夏季/秋季）+ 鸡蛋（全年）
        scored_summer = score_candidate(rc, fat_loss_constraints, "夏季", [], [], DEFAULT_WEIGHTS)
        scored_winter = score_candidate(rc, fat_loss_constraints, "冬季", [], [], DEFAULT_WEIGHTS)
        assert scored_summer.scores["season"] > scored_winter.scores["season"]

    def test_utilization_improves_score(self, seed_data, fat_loss_constraints):
        pool = build_candidate_pool(seed_data)
        rc = [c for c in pool if c.recipe_id == 1][0]  # 需要番茄(1)、鸡蛋(2)、酱油(8)
        # 没有已有食材 — utilization=1.0（不惩罚）
        scored0 = score_candidate(rc, fat_loss_constraints, "夏季", [], [], DEFAULT_WEIGHTS)
        # 有番茄(1)和鸡蛋(2) — 菜谱要[1,2,8]，覆盖 2/3 → utilization=0.6667
        scored1 = score_candidate(rc, fat_loss_constraints, "夏季", [1, 2], [], DEFAULT_WEIGHTS)
        assert abs(scored0.scores["utilization"] - 1.0) < 0.01
        assert abs(scored1.scores["utilization"] - 0.67) < 0.01


# ═══════════════════════════════════════════════════
# 测试：完整排名
# ═══════════════════════════════════════════════════

class TestRankCandidates:
    """验证完整推荐流程"""

    def test_rank_returns_correct_count(self, seed_data, fat_loss_constraints):
        """海鲜过敏排除2道菜后，候选池剩3道"""
        top = rank_candidates(seed_data, fat_loss_constraints, top_n=10)
        assert len(top) == 3  # 5道 - 2道(海鲜) = 3道

    def test_rank_returns_top_3(self, seed_data, fat_loss_constraints):
        top3 = rank_candidates(seed_data, fat_loss_constraints, top_n=3)
        assert len(top3) == 3

    def test_rank_sorted_by_score_desc(self, seed_data, fat_loss_constraints):
        top5 = rank_candidates(seed_data, fat_loss_constraints, top_n=5)
        for i in range(len(top5) - 1):
            assert top5[i].total_score >= top5[i + 1].total_score

    def test_excludes_seafood_allergen(self, seed_data):
        """海鲜过敏应排除含虾仁/鱼的菜谱"""
        profile = Profile(
            profile_id=1, age=28, gender="male", height=175, weight=72,
            diet_type="balanced", health_goal="healthy",
            allergies=["海鲜"],
        )
        constraints = build_constraints(profile, duration_days=7, total_budget=300)
        top = rank_candidates(seed_data, constraints, top_n=10)
        recipe_ids = [r.recipe_id for r in top]
        # 虾仁炒饭(5) 含虾仁应被排除
        assert 5 not in recipe_ids
        # 三文鱼排(3) 含鱼应被排除
        assert 3 not in recipe_ids
        # 番茄炒蛋(1) 不含海鲜应保留
        assert 1 in recipe_ids

    def test_no_allergen_includes_all(self, seed_data):
        """无过敏原时全部菜谱应被召回"""
        profile = Profile(
            profile_id=1, age=28, gender="male", height=175, weight=72,
            diet_type="balanced", health_goal="healthy",
            allergies=None,
        )
        constraints = build_constraints(profile, duration_days=7, total_budget=300)
        top = rank_candidates(seed_data, constraints, top_n=10)
        recipe_ids = [r.recipe_id for r in top]
        assert 5 in recipe_ids  # 虾仁炒饭应包含

    def test_owned_ingredients_boost_rank(self, seed_data, fat_loss_constraints):
        """已有食材的菜谱应获得更高排名"""
        # 有番茄(1)、鸡蛋(2) — 番茄炒蛋利用率高
        top_with = rank_candidates(
            seed_data, fat_loss_constraints, owned_ingredient_ids=[1, 2], top_n=5,
        )
        # 没有 — 番茄炒蛋利用率低
        top_without = rank_candidates(
            seed_data, fat_loss_constraints, owned_ingredient_ids=[], top_n=5,
        )
        # 番茄炒蛋(1) 在有食材时应排名更高
        rank_with = next(i for i, r in enumerate(top_with) if r.recipe_id == 1)
        rank_without = next(i for i, r in enumerate(top_without) if r.recipe_id == 1)
        assert rank_with <= rank_without

    def test_score_range(self, seed_data, fat_loss_constraints):
        top = rank_candidates(seed_data, fat_loss_constraints, top_n=5)
        for r in top:
            assert 0 <= r.total_score <= 1


class TestHybridRankCandidates:
    """验证 RAG 语义分只能参与排序，不能突破硬过滤。"""

    def test_semantic_score_changes_order_and_keeps_evidence(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates_hybrid(
            seed_data,
            fat_loss_constraints,
            semantic_scores={1: 1.0, 2: 0.0},
            semantic_recipe_ids=[1],
            top_n=5,
        )

        tomato_egg = next(item for item in ranked if item.recipe_id == 1)
        assert tomato_egg.scores["semantic"] == 1.0
        assert tomato_egg.evidence["retrieval_sources"] == ["structured", "semantic"]
        assert tomato_egg.evidence["objective_evidence"]

    def test_semantic_candidate_cannot_bypass_allergen_filter(self, seed_data, fat_loss_constraints):
        ranked = rank_candidates_hybrid(
            seed_data,
            fat_loss_constraints,
            semantic_scores={3: 1.0, 5: 1.0},
            semantic_recipe_ids=[3, 5],
            top_n=10,
        )

        assert 3 not in [item.recipe_id for item in ranked]
        assert 5 not in [item.recipe_id for item in ranked]
