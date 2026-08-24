"""Deterministic weekly meal optimizer for normalized AI recipe candidates."""

from __future__ import annotations

import math
from collections import Counter

from pydantic import BaseModel, Field

from app.config import settings
from app.services.ai_plan_models import GeneratedMeal, GeneratedPlan, GeneratedRecipe


class PlanOptimizationError(RuntimeError):
    def __init__(self, message: str, *, feedback: dict | None = None):
        super().__init__(message)
        self.feedback = feedback or {"message": message}


class PlanOptimizationResult(BaseModel):
    plan: GeneratedPlan
    unique_recipe_count: int
    max_recipe_repeat: int
    adjacent_duplicate_count: int
    cuisine_count: int
    primary_protein_count: int
    meal_count: int
    required_unique_count: int
    selected_recipe_indexes: list[int] = Field(default_factory=list)


def meal_slots_for_intent(intent: dict | None) -> list[str]:
    meal_count = max(1, min(int((intent or {}).get("meal_count_per_day") or 3), 3))
    if meal_count == 1:
        return ["dinner"]
    if meal_count == 2:
        return ["lunch", "dinner"]
    return ["breakfast", "lunch", "dinner"]


def candidate_target(duration_days: int, intent: dict | None = None) -> int:
    meal_total = duration_days * len(meal_slots_for_intent(intent))
    return max(settings.PLAN_CANDIDATE_MIN, min(settings.PLAN_CANDIDATE_MAX, meal_total + 6))


def required_unique_count(duration_days: int, intent: dict | None = None) -> int:
    total_meals = duration_days * len(meal_slots_for_intent(intent))
    ratio_target = math.ceil(total_meals * settings.PLAN_MIN_UNIQUE_RATIO)
    return min(total_meals, max(ratio_target, duration_days * 2))


def _primary_protein(recipe: GeneratedRecipe) -> str:
    protein_tokens = (
        "鸡胸肉", "鸡腿肉", "鸡蛋", "猪里脊肉", "猪肉丝", "牛肉", "牛腩", "牛排",
        "虾仁", "鲈鱼", "鳕鱼", "三文鱼", "金枪鱼罐头", "豆腐", "牛奶", "酸奶",
    )
    names = [item.catalog_name or item.name for item in recipe.ingredients]
    for token in protein_tokens:
        if any(token in name for name in names):
            return token
    return "其他"


def _closeness(actual: float, target: float) -> float:
    if target <= 0:
        return 0.5
    return max(0.0, 1.0 - abs(actual - target) / target)


def _slot_weights(slots: list[str]) -> dict[str, float]:
    if slots == ["breakfast", "lunch", "dinner"]:
        return {"breakfast": 0.25, "lunch": 0.40, "dinner": 0.35}
    if slots == ["lunch", "dinner"]:
        return {"lunch": 0.45, "dinner": 0.55}
    return {slots[0]: 1.0}


def _candidate_score(
    recipe: GeneratedRecipe,
    *,
    slot: str,
    slot_weight: float,
    daily_calorie_target: float,
    daily_protein_target: float,
    per_meal_budget: float,
    usage: int,
    cuisine_usage: Counter[str],
    protein_usage: Counter[str],
    cooking_time_limit: float,
) -> float:
    nutrition = recipe.nutrition_estimate
    if nutrition is None or recipe.cost_estimate is None:
        return -1_000.0
    calorie_score = _closeness(nutrition.calories, daily_calorie_target * slot_weight)
    protein_score = _closeness(nutrition.protein_g, daily_protein_target * slot_weight)
    budget_score = _closeness(recipe.cost_estimate, per_meal_budget) if per_meal_budget else 0.5
    cuisine_score = 1 / (1 + cuisine_usage[recipe.cuisine_type])
    protein = _primary_protein(recipe)
    protein_score_diversity = 1 / (1 + protein_usage[protein])
    total_time = recipe.prep_time_min + recipe.cook_time_min
    time_score = 1.0 if not cooking_time_limit or total_time <= cooking_time_limit else max(0.0, cooking_time_limit / total_time)
    unused_bonus = 0.6 if usage == 0 else 0.0
    return (
        0.35 * calorie_score
        + 0.20 * protein_score
        + 0.15 * budget_score
        + 0.15 * cuisine_score
        + 0.10 * protein_score_diversity
        + 0.05 * time_score
        + unused_bonus
        - usage * 0.30
    )


def optimize_weekly_plan(
    plan: GeneratedPlan,
    constraints: dict,
    *,
    intent: dict | None,
    duration_days: int,
) -> PlanOptimizationResult:
    slots = meal_slots_for_intent(intent)
    total_meals = duration_days * len(slots)
    required_unique = required_unique_count(duration_days, intent)
    max_repeat = settings.PLAN_MAX_RECIPE_REPEAT

    eligible_indexes = [
        index
        for index, recipe in enumerate(plan.recipes)
        if recipe.nutrition_estimate is not None
        and recipe.cost_estimate is not None
        and all(item.ingredient_id is not None and item.data_source for item in recipe.ingredients)
    ]
    unique_names = {plan.recipes[index].name.strip().lower() for index in eligible_indexes}
    if len(unique_names) < required_unique:
        raise PlanOptimizationError(
            f"可用候选只有 {len(unique_names)} 道，至少需要 {required_unique} 道不同菜品。",
            feedback={
                "code": "candidate_shortage",
                "eligible_candidate_count": len(unique_names),
                "required_unique_count": required_unique,
                "requested_candidate_target": candidate_target(duration_days, intent),
            },
        )
    if len(eligible_indexes) * max_repeat < total_meals:
        raise PlanOptimizationError(
            "候选数量不足，无法在重复上限内填满全部餐次。",
            feedback={
                "code": "repeat_capacity_shortage",
                "eligible_candidate_count": len(eligible_indexes),
                "meal_count": total_meals,
                "max_recipe_repeat": max_repeat,
            },
        )

    calorie_min = float(constraints.get("calorie_min") or 0)
    calorie_max = float(constraints.get("calorie_max") or 0)
    daily_calorie_target = (calorie_min + calorie_max) / 2 if calorie_min and calorie_max else max(calorie_min, calorie_max, 2000)
    daily_protein_target = float(constraints.get("target_protein") or 0)
    total_budget = float(constraints.get("total_budget") or 0)
    per_meal_budget = total_budget / total_meals if total_budget else 0
    semantic = (intent or {}).get("semantic_preferences") or {}
    cooking_time_limit = float(
        (intent or {}).get("max_cooking_time")
        or semantic.get("max_cooking_time")
        or 0
    )
    weights = _slot_weights(slots)

    usage: Counter[int] = Counter()
    cuisine_usage: Counter[str] = Counter()
    protein_usage: Counter[str] = Counter()
    selected: list[int] = []
    meals: list[GeneratedMeal] = []
    last_index: int | None = None

    for day in range(1, duration_days + 1):
        for slot in slots:
            available = []
            remaining_slots = total_meals - len(selected)
            still_needed_unique = max(0, required_unique - len(set(selected)))
            force_unused = still_needed_unique >= remaining_slots
            for index in eligible_indexes:
                recipe = plan.recipes[index]
                if usage[index] >= max_repeat or index == last_index:
                    continue
                if recipe.meal_slots and slot not in recipe.meal_slots:
                    continue
                if force_unused and usage[index] > 0:
                    continue
                score = _candidate_score(
                    recipe,
                    slot=slot,
                    slot_weight=weights[slot],
                    daily_calorie_target=daily_calorie_target,
                    daily_protein_target=daily_protein_target,
                    per_meal_budget=per_meal_budget,
                    usage=usage[index],
                    cuisine_usage=cuisine_usage,
                    protein_usage=protein_usage,
                    cooking_time_limit=cooking_time_limit,
                )
                available.append((score, recipe.name, index))

            if not available:
                raise PlanOptimizationError(
                    f"无法为第 {day} 天 {slot} 找到满足硬约束的候选菜品。",
                    feedback={
                        "code": "meal_slot_unfillable",
                        "day": day,
                        "slot": slot,
                        "selected_count": len(selected),
                        "required_unique_count": required_unique,
                    },
                )

            _, _, chosen = sorted(available, key=lambda item: (-item[0], item[1], item[2]))[0]
            recipe = plan.recipes[chosen]
            meals.append(GeneratedMeal(day=day, slot=slot, recipe_index=chosen, servings=1))
            selected.append(chosen)
            usage[chosen] += 1
            cuisine_usage[recipe.cuisine_type] += 1
            protein_usage[_primary_protein(recipe)] += 1
            last_index = chosen

    unique_count = len(set(selected))
    if unique_count < required_unique:
        raise PlanOptimizationError(
            f"优化后只有 {unique_count} 道不同菜品，低于要求的 {required_unique} 道。",
            feedback={
                "code": "unique_target_unmet",
                "unique_recipe_count": unique_count,
                "required_unique_count": required_unique,
            },
        )

    optimized = plan.model_copy(deep=True)
    optimized.meals = meals
    adjacent_duplicates = sum(1 for left, right in zip(selected, selected[1:]) if left == right)
    return PlanOptimizationResult(
        plan=optimized,
        unique_recipe_count=unique_count,
        max_recipe_repeat=max(usage.values(), default=0),
        adjacent_duplicate_count=adjacent_duplicates,
        cuisine_count=len(cuisine_usage),
        primary_protein_count=len(protein_usage),
        meal_count=len(meals),
        required_unique_count=required_unique,
        selected_recipe_indexes=selected,
    )
