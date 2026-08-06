"""推荐引擎 — 召回 → 排除 → 评分 → 排序 → TOP N"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.services.constraint_analyzer import ConstraintSet
from app.services.scoring import (
    health_score,
    budget_score,
    preference_score,
    season_score,
    utilization_score,
)
from app.services.recipe_service import get_recipe_ingredients

# ─── 评分权重（六维，和为 1.0）──────────────────────

DEFAULT_WEIGHTS: Dict[str, float] = {
    "health": 0.30,
    "budget": 0.20,
    "preference": 0.20,
    "season": 0.10,
    "variety": 0.10,
    "utilization": 0.10,
}

# RAG 混合重排权重。客观数据仍由代码计算，语义分只影响口味/场景维度。
HYBRID_WEIGHTS: Dict[str, float] = {
    "health": 0.25,
    "budget": 0.10,
    "preference": 0.07,
    "semantic": 0.35,
    "season": 0.08,
    "variety": 0.05,
    "utilization": 0.10,
}

# ─── 常见过敏原 → 食材名称关键词 ─────────────────

ALLERGEN_KEYWORDS: Dict[str, List[str]] = {
    "海鲜": ["虾", "蟹", "鱼", "贝", "蛤", "蚝", "鲍", "鱿", "海"],
    "花生": ["花生"],
    "牛奶": ["牛奶", "乳制品", "芝士", "黄油", "奶油"],
    "鸡蛋": ["鸡蛋", "蛋"],
    "大豆": ["大豆", "豆腐", "豆浆", "豆干", "豆皮"],
    "麸质": ["面粉", "面条", "面包", "麦", "麸"],
    "坚果": ["杏仁", "核桃", "腰果", "松子", "榛子"],
}


@dataclass
class RecipeCandidate:
    """候选菜谱 — 包含所有评分需要的数据"""

    recipe_id: int
    name: str
    category: str
    cuisine_type: str
    difficulty: str
    prep_time: int
    cook_time: int
    servings: int
    tags: List[str]
    total_calories: float
    estimated_cost: float
    ingredient_ids: List[int]
    ingredient_categories: List[str]
    ingredient_seasons: List[Optional[List[str]]]
    image_url: Optional[str]
    ingredient_names: List[str] = field(default_factory=list)


def build_candidate_pool(db: Session) -> List[RecipeCandidate]:
    """从数据库召回所有菜谱，构建候选池

    批量加载所有菜谱及其食材信息，减少数据库查询次数。
    """
    # 1. 加载所有食材（一次查询）
    ingredients_map = {
        ing.ingredient_id: ing
        for ing in db.query(Ingredient).all()
    }

    # 2. 加载所有菜谱
    recipes = db.query(Recipe).all()

    candidates = []
    for recipe in recipes:
        ingredients = get_recipe_ingredients(db, recipe.recipe_id)

        ing_ids = []
        ing_cats = []
        ing_seasons = []
        ing_names = []
        total_cost = 0.0

        for ing_data in ingredients:
            ing_id = ing_data["ingredient_id"]
            ing_ids.append(ing_id)
            ing_names.append(ing_data["name"])
            ing_cats.append(ing_data["category"])
            total_cost += ing_data["estimated_cost"]

            ing = ingredients_map.get(ing_id)
            ing_seasons.append(ing.season_tags if ing else None)

        candidates.append(RecipeCandidate(
            recipe_id=recipe.recipe_id,
            name=recipe.name,
            category=recipe.category,
            cuisine_type=recipe.cuisine_type,
            difficulty=recipe.difficulty,
            prep_time=recipe.prep_time,
            cook_time=recipe.cook_time,
            servings=recipe.servings,
            tags=recipe.tags or [],
            total_calories=float(recipe.total_calories),
            estimated_cost=round(total_cost, 2),
            ingredient_ids=ing_ids,
            ingredient_categories=ing_cats,
            ingredient_seasons=ing_seasons,
            image_url=recipe.image_url,
            ingredient_names=ing_names,
        ))

    return candidates


def resolve_allergen_ingredient_ids(
    db: Session,
    allergen_names: List[str],
) -> List[int]:
    """将过敏原名称解析为需要排除的食材 ID

    先用精确匹配找食材名，再通过 ALLERGEN_KEYWORDS 映射做关键词匹配。
    """
    if not allergen_names:
        return []

    all_ingredients = db.query(Ingredient).all()
    excluded_ids = set()

    for name in allergen_names:
        keywords = ALLERGEN_KEYWORDS.get(name, [name])

        for ing in all_ingredients:
            for kw in keywords:
                if kw in ing.name:
                    excluded_ids.add(ing.ingredient_id)
                    break

    return list(excluded_ids)


def exclude_recipes(
    pool: List[RecipeCandidate],
    excluded_ingredient_ids: set,
) -> List[RecipeCandidate]:
    """从候选池中排除含有指定食材的菜谱"""
    if not excluded_ingredient_ids:
        return pool

    return [
        c for c in pool
        if not (excluded_ingredient_ids & set(c.ingredient_ids))
    ]


def exclude_diet_incompatible_recipes(
    pool: List[RecipeCandidate],
    diet_type: str,
) -> List[RecipeCandidate]:
    """处理不能由排序分数抵消的严格饮食类型限制。"""
    if diet_type == "vegan":
        animal_categories = {"meat", "seafood", "egg", "dairy"}
        return [
            candidate for candidate in pool
            if not (animal_categories & set(candidate.ingredient_categories))
        ]
    if diet_type == "gluten_free":
        gluten_keywords = ("面", "麦", "燕麦", "面包", "意面")
        return [
            candidate for candidate in pool
            if not any(keyword in name for name in candidate.ingredient_names for keyword in gluten_keywords)
        ]
    if diet_type == "keto":
        return [
            candidate for candidate in pool
            if "grain" not in candidate.ingredient_categories
            and not any(tag in {"主食", "高碳水"} for tag in candidate.tags)
        ]
    return pool


@dataclass
class ScoredRecipe:
    """评分后的菜谱结果"""

    recipe_id: int
    name: str
    category: str
    cuisine_type: str
    difficulty: str
    prep_time: int
    cook_time: int
    servings: int
    image_url: Optional[str]
    total_calories: float
    estimated_cost: float
    scores: Dict[str, float]
    total_score: float
    evidence: Dict[str, Any] = field(default_factory=dict)


def score_candidate(
    candidate: RecipeCandidate,
    constraints: ConstraintSet,
    current_season: str,
    owned_ids: List[int],
    already_selected: List[dict],
    weights: Dict[str, float],
) -> ScoredRecipe:
    """对单个候选菜谱计算六维评分和总分"""
    # 单道菜按餐次目标评分，避免用每日 1800kcal 目标给每一餐打分。
    h = health_score(
        candidate.total_calories,
        constraints.calorie_min / 3,
        constraints.calorie_max / 3,
    )
    b = budget_score(constraints.daily_budget, candidate.estimated_cost)
    p = preference_score(
        constraints.diet_type,
        constraints.health_goal,
        candidate.tags,
        ingredient_categories=candidate.ingredient_categories,
    )
    s = season_score(candidate.ingredient_seasons, current_season)
    u = utilization_score(candidate.ingredient_ids, owned_ids)

    # variety_score 依赖已选菜谱列表，在周计划阶段动态计算
    # 初始排名时已选列表为空，所有菜谱 variety=1.0

    total = (
        weights["health"] * h
        + weights["budget"] * b
        + weights["preference"] * p
        + weights["season"] * s
        + weights["variety"] * 1.0
        + weights["utilization"] * u
    )

    return ScoredRecipe(
        recipe_id=candidate.recipe_id,
        name=candidate.name,
        category=candidate.category,
        cuisine_type=candidate.cuisine_type,
        difficulty=candidate.difficulty,
        prep_time=candidate.prep_time,
        cook_time=candidate.cook_time,
        servings=candidate.servings,
        image_url=candidate.image_url,
        total_calories=candidate.total_calories,
        estimated_cost=candidate.estimated_cost,
        scores={"health": h, "budget": b, "preference": p,
                "season": s, "variety": 1.0, "utilization": u},
        total_score=round(total, 4),
    )


def rank_candidates(
    db: Session,
    constraints: ConstraintSet,
    current_season: str = "夏季",
    owned_ingredient_ids: Optional[List[int]] = None,
    weights: Optional[Dict[str, float]] = None,
    top_n: int = 15,
) -> List[ScoredRecipe]:
    """召回 → 排除 → 评分 → 排序 → 返回 TOP N

    Args:
        db: 数据库会话
        constraints: 约束集
        current_season: 当前季节
        owned_ingredient_ids: 用户已有食材 ID 列表
        weights: 评分权重，默认使用 DEFAULT_WEIGHTS
        top_n: 返回前 N 个结果

    Returns:
        评分降序排列的 TOP N 菜谱列表
    """
    w = weights or DEFAULT_WEIGHTS
    owned_ids = owned_ingredient_ids or []

    # 1. 召回全部菜谱
    pool = build_candidate_pool(db)

    # 2. 解析过敏原 → 排除
    allergen_ids = resolve_allergen_ingredient_ids(db, constraints.allergen_names)
    excluded = set(constraints.excluded_ingredient_ids + allergen_ids)
    pool = exclude_recipes(pool, excluded)
    pool = exclude_diet_incompatible_recipes(pool, constraints.diet_type)

    # 3. 逐道评分
    scored = []
    for candidate in pool:
        result = score_candidate(candidate, constraints, current_season, owned_ids, [], w)
        scored.append(result)

    # 4. 按总分降序排列
    scored.sort(key=lambda r: r.total_score, reverse=True)

    return scored[:top_n]


def build_recommendation_evidence(
    recipe: ScoredRecipe,
    constraints: ConstraintSet,
    retrieval_sources: list[str],
) -> Dict[str, Any]:
    """生成由代码得出的可追溯推荐证据，供 API 和 LLM 总结复用。"""
    matched_preferences: list[str] = []
    warnings: list[str] = []
    if recipe.scores.get("semantic", 0) >= 0.65:
        matched_preferences.append("语义偏好与菜谱场景匹配")
    if recipe.scores["budget"] >= 0.8:
        matched_preferences.append("餐均预算匹配")
    if recipe.scores["utilization"] >= 0.5:
        matched_preferences.append("可利用已有食材")
    if recipe.estimated_cost > constraints.daily_budget / 3 and constraints.daily_budget > 0:
        warnings.append("单餐预估成本高于平均餐均预算")
    if recipe.scores["health"] < 0.6:
        warnings.append("单份热量与目标区间存在偏差，需由周计划搭配调整")

    return {
        "matched_preferences": matched_preferences,
        "objective_evidence": [
            {
                "type": "calories",
                "actual": round(recipe.total_calories, 1),
                "target_range": [round(constraints.calorie_min / 3, 1), round(constraints.calorie_max / 3, 1)],
            },
            {
                "type": "cost",
                "actual": round(recipe.estimated_cost, 2),
                "daily_budget": round(constraints.daily_budget, 2),
            },
        ],
        "retrieval_sources": retrieval_sources,
        "warnings": warnings,
    }


def rank_candidates_hybrid(
    db: Session,
    constraints: ConstraintSet,
    semantic_scores: Optional[Dict[int, float]] = None,
    semantic_recipe_ids: Optional[List[int]] = None,
    current_season: str = "夏季",
    owned_ingredient_ids: Optional[List[int]] = None,
    top_n: int = 15,
    weights: Optional[Dict[str, float]] = None,
) -> List[ScoredRecipe]:
    """结构化候选与 RAG 语义候选融合后的确定性重排。

    所有数据库菜谱构成结构化召回集；RAG 命中的菜谱附加语义分。
    过敏原过滤发生在任何加权之前，语义分不能绕过硬约束。
    """
    semantic_scores = semantic_scores or {}
    semantic_ids = set(semantic_recipe_ids or semantic_scores.keys())
    owned_ids = owned_ingredient_ids or []
    w = weights or HYBRID_WEIGHTS

    pool = build_candidate_pool(db)
    allergen_ids = resolve_allergen_ingredient_ids(db, constraints.allergen_names)
    excluded = set(constraints.excluded_ingredient_ids + allergen_ids)
    eligible_pool = exclude_recipes(pool, excluded)
    eligible_pool = exclude_diet_incompatible_recipes(eligible_pool, constraints.diet_type)

    ranked: List[ScoredRecipe] = []
    for candidate in eligible_pool:
        baseline = score_candidate(
            candidate, constraints, current_season, owned_ids, [], DEFAULT_WEIGHTS,
        )
        semantic = max(0.0, min(1.0, float(semantic_scores.get(candidate.recipe_id, 0.0))))
        scores = {**baseline.scores, "semantic": round(semantic, 4)}
        total = (
            w["health"] * scores["health"]
            + w["budget"] * scores["budget"]
            + w["preference"] * scores["preference"]
            + w["semantic"] * scores["semantic"]
            + w["season"] * scores["season"]
            + w["variety"] * scores["variety"]
            + w["utilization"] * scores["utilization"]
        )
        sources = ["structured"]
        if candidate.recipe_id in semantic_ids:
            sources.append("semantic")
        recipe = ScoredRecipe(
            recipe_id=baseline.recipe_id,
            name=baseline.name,
            category=baseline.category,
            cuisine_type=baseline.cuisine_type,
            difficulty=baseline.difficulty,
            prep_time=baseline.prep_time,
            cook_time=baseline.cook_time,
            servings=baseline.servings,
            image_url=baseline.image_url,
            total_calories=baseline.total_calories,
            estimated_cost=baseline.estimated_cost,
            scores=scores,
            total_score=round(total, 4),
        )
        recipe.evidence = build_recommendation_evidence(recipe, constraints, sources)
        ranked.append(recipe)

    ranked.sort(key=lambda item: item.total_score, reverse=True)
    return ranked[:top_n]
