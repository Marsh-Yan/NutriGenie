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
    portion_scale_by_recipe: dict[int, float] = Field(default_factory=dict)


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


def _scaled_nutrition(value, factor: float):
    return value.model_copy(
        update={
            "calories": round(value.calories * factor, 2),
            "protein_g": round(value.protein_g * factor, 2),
            "fat_g": round(value.fat_g * factor, 2),
            "carbs_g": round(value.carbs_g * factor, 2),
            "fiber_g": round(value.fiber_g * factor, 2),
        }
    )


def _expected_portion_factor(recipe: GeneratedRecipe, calorie_target: float) -> float:
    nutrition = recipe.nutrition_estimate
    if nutrition is None or nutrition.calories <= 0:
        return 1.0
    return max(0.5, min(calorie_target / nutrition.calories, 2.5))


def _calibrate_selected_portions(
    plan: GeneratedPlan,
    meals: list[GeneratedMeal],
    *,
    daily_calorie_target: float,
    slot_weights: dict[str, float],
) -> dict[int, float]:
    """Scale trusted ingredient facts to realistic per-slot portion targets.

    The LLM creates the recipe and ingredient composition. The deterministic
    layer calibrates only quantities after normalization, so every derived
    nutrient and cost remains traceable to the ingredient catalog.
    """
    slots_by_recipe: dict[int, list[str]] = {}
    for meal in meals:
        slots_by_recipe.setdefault(meal.recipe_index, []).append(meal.slot)

    scales: dict[int, float] = {}
    for recipe_index, assigned_slots in slots_by_recipe.items():
        recipe = plan.recipes[recipe_index]
        nutrition = recipe.nutrition_estimate
        if nutrition is None or nutrition.calories <= 0:
            continue
        target = sum(daily_calorie_target * slot_weights[slot] for slot in assigned_slots) / len(assigned_slots)
        # Guard against pathological model quantities while still allowing a
        # normal single serving to be calibrated into a full lunch or dinner.
        factor = max(0.5, min(target / nutrition.calories, 2.5))
        factor = round(factor, 4)
        if abs(factor - 1) < 0.01:
            scales[recipe_index] = 1.0
            continue

        for ingredient in recipe.ingredients:
            ingredient.quantity = round(ingredient.quantity * factor, 2)
            if ingredient.estimated_grams is not None:
                ingredient.estimated_grams = round(ingredient.estimated_grams * factor, 2)
            if ingredient.nutrition_estimate is not None:
                ingredient.nutrition_estimate = _scaled_nutrition(ingredient.nutrition_estimate, factor)
            if ingredient.line_cost_estimate is not None:
                ingredient.line_cost_estimate = round(ingredient.line_cost_estimate * factor, 2)

        recipe.nutrition_estimate = _scaled_nutrition(nutrition, factor)
        recipe.cost_estimate = round(float(recipe.cost_estimate or 0) * factor, 2)
        recipe.servings = 1
        note = f"后端依据食材目录将该餐份量校准为原配方的 {factor:.2f} 倍。"
        recipe.generation_note = f"{recipe.generation_note} {note}".strip()
        scales[recipe_index] = factor
    return scales


def _candidate_score(
    recipe: GeneratedRecipe,
    *,
    slot: str,
    slot_weight: float,
    daily_calorie_target: float,
    daily_protein_target: float,
    protein_needed: float,
    per_meal_budget: float,
    usage: int,
    cuisine_usage: Counter[str],
    protein_usage: Counter[str],
    cooking_time_limit: float,
) -> float:
    nutrition = recipe.nutrition_estimate
    if nutrition is None or recipe.cost_estimate is None:
        return -1_000.0
    slot_calorie_target = daily_calorie_target * slot_weight
    projected_factor = _expected_portion_factor(recipe, slot_calorie_target)
    calorie_score = _closeness(nutrition.calories * projected_factor, slot_calorie_target)
    projected_protein = nutrition.protein_g * projected_factor
    protein_score = min(1.0, projected_protein / protein_needed) if protein_needed > 0 else 0.5
    projected_cost = recipe.cost_estimate * projected_factor
    budget_score = min(1.0, per_meal_budget / max(projected_cost, 0.01)) if per_meal_budget else 0.5
    over_budget_penalty = (
        max(0.0, projected_cost / per_meal_budget - 1.0) * 1.2
        if per_meal_budget else 0.0
    )
    cuisine_score = 1 / (1 + cuisine_usage[recipe.cuisine_type])
    protein = _primary_protein(recipe)
    protein_score_diversity = 1 / (1 + protein_usage[protein])
    total_time = recipe.prep_time_min + recipe.cook_time_min
    time_score = 1.0 if not cooking_time_limit or total_time <= cooking_time_limit else max(0.0, cooking_time_limit / total_time)
    unused_bonus = 0.35 if usage == 0 else 0.0
    return (
        0.20 * calorie_score
        + 0.40 * protein_score
        + 0.25 * budget_score
        + 0.10 * cuisine_score
        + 0.05 * protein_score_diversity
        + 0.05 * time_score
        + unused_bonus
        - usage * 0.30
        - over_budget_penalty
    )


def _rebalance_daily_protein(
    plan: GeneratedPlan,
    meals: list[GeneratedMeal],
    *,
    daily_calorie_target: float,
    slot_weights: dict[str, float],
    daily_protein_target: float,
) -> None:
    """Redistribute selected dishes across days without changing the recipe pool."""
    if daily_protein_target <= 0 or not meals:
        return

    def projected_protein(meal: GeneratedMeal) -> float:
        recipe = plan.recipes[meal.recipe_index]
        nutrition = recipe.nutrition_estimate
        if nutrition is None:
            return 0.0
        factor = _expected_portion_factor(recipe, daily_calorie_target * slot_weights[meal.slot])
        return nutrition.protein_g * factor

    threshold = daily_protein_target * 0.85
    totals: dict[int, float] = {}
    for meal in meals:
        totals[meal.day] = totals.get(meal.day, 0.0) + projected_protein(meal)

    def deficit_score() -> float:
        return sum(max(0.0, threshold - value) ** 2 for value in totals.values())

    for _ in range(len(meals) * 2):
        current_score = deficit_score()
        best: tuple[float, int, int] | None = None
        for left in range(len(meals)):
            for right in range(left + 1, len(meals)):
                first, second = meals[left], meals[right]
                if first.day == second.day or first.slot != second.slot:
                    continue
                left_protein, right_protein = projected_protein(first), projected_protein(second)
                next_left = totals[first.day] - left_protein + right_protein
                next_right = totals[second.day] - right_protein + left_protein
                new_score = (
                    current_score
                    - max(0.0, threshold - totals[first.day]) ** 2
                    - max(0.0, threshold - totals[second.day]) ** 2
                    + max(0.0, threshold - next_left) ** 2
                    + max(0.0, threshold - next_right) ** 2
                )
                if new_score >= current_score - 1e-6:
                    continue
                sequence = [meal.recipe_index for meal in meals]
                sequence[left], sequence[right] = sequence[right], sequence[left]
                if any(a == b for a, b in zip(sequence, sequence[1:])):
                    continue
                if best is None or new_score < best[0]:
                    best = (new_score, left, right)
        if best is None:
            break
        _, left, right = best
        first, second = meals[left], meals[right]
        left_protein, right_protein = projected_protein(first), projected_protein(second)
        totals[first.day] += right_protein - left_protein
        totals[second.day] += left_protein - right_protein
        first.recipe_index, second.recipe_index = second.recipe_index, first.recipe_index


def _refine_quality_targets(
    plan: GeneratedPlan,
    meals: list[GeneratedMeal],
    eligible_indexes: list[int],
    *,
    daily_calorie_target: float,
    daily_protein_target: float,
    total_budget: float,
    required_unique: int,
    max_repeat: int,
    slot_weights: dict[str, float],
) -> None:
    """Replace selected candidates when the whole-week targets are still missed."""
    if not meals:
        return

    def contribution(index: int, slot: str) -> tuple[float, float, float]:
        recipe = plan.recipes[index]
        nutrition = recipe.nutrition_estimate
        if nutrition is None:
            return (0.0, 0.0, 0.0)
        factor = _expected_portion_factor(recipe, daily_calorie_target * slot_weights[slot])
        return (
            nutrition.calories * factor,
            nutrition.protein_g * factor,
            float(recipe.cost_estimate or 0) * factor,
        )

    def objective(sequence: list[int]) -> float:
        daily: dict[int, list[float]] = {}
        cost = 0.0
        for meal, index in zip(meals, sequence):
            calories, protein, meal_cost = contribution(index, meal.slot)
            totals = daily.setdefault(meal.day, [0.0, 0.0])
            totals[0] += calories
            totals[1] += protein
            cost += meal_cost
        score = 0.0
        if len(slot_weights) == 3 and daily_calorie_target > 0:
            tolerance = settings.PLAN_CALORIE_TOLERANCE
            for calories, _ in daily.values():
                excess = max(0.0, abs(calories / daily_calorie_target - 1.0) - tolerance)
                score += excess * excess
        if len(slot_weights) == 3 and daily_protein_target > 0:
            for _, protein in daily.values():
                shortfall = max(0.0, 0.85 - protein / daily_protein_target)
                score += shortfall * shortfall
        if total_budget > 0:
            over = max(0.0, cost / total_budget - 1.0 - settings.PLAN_BUDGET_TOLERANCE)
            score += over * over
        return score

    selected = [meal.recipe_index for meal in meals]
    for _ in range(min(30, len(meals) * 2)):
        baseline = objective(selected)
        if baseline < 1e-8:
            break
        usage = Counter(selected)
        best: tuple[float, int, int] | None = None
        for position, meal in enumerate(meals):
            old_index = selected[position]
            for index in eligible_indexes:
                if index == old_index or usage[index] >= max_repeat:
                    continue
                recipe = plan.recipes[index]
                if recipe.meal_slots and meal.slot not in recipe.meal_slots:
                    continue
                if usage[old_index] == 1 and usage[index] > 0 and len(usage) <= required_unique:
                    continue
                if (position > 0 and selected[position - 1] == index) or (
                    position + 1 < len(selected) and selected[position + 1] == index
                ):
                    continue
                selected[position] = index
                score = objective(selected)
                selected[position] = old_index
                if score < baseline - 1e-8 and (best is None or score < best[0]):
                    best = (score, position, index)
        if best is None:
            break
        _, position, index = best
        selected[position] = index
        meals[position].recipe_index = index


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
        day_protein_estimate = 0.0
        for slot_index, slot in enumerate(slots):
            available = []
            remaining_slots = total_meals - len(selected)
            still_needed_unique = max(0, required_unique - len(set(selected)))
            force_unused = still_needed_unique >= remaining_slots
            remaining_day_slots = len(slots) - slot_index
            protein_needed = max(
                daily_protein_target * weights[slot],
                (daily_protein_target - day_protein_estimate) / remaining_day_slots,
            )
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
                    protein_needed=protein_needed,
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
            if recipe.nutrition_estimate is not None:
                factor = _expected_portion_factor(recipe, daily_calorie_target * weights[slot])
                day_protein_estimate += recipe.nutrition_estimate.protein_g * factor
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

    _refine_quality_targets(
        plan,
        meals,
        eligible_indexes,
        daily_calorie_target=daily_calorie_target,
        daily_protein_target=daily_protein_target,
        total_budget=total_budget,
        required_unique=required_unique,
        max_repeat=max_repeat,
        slot_weights=weights,
    )
    _rebalance_daily_protein(
        plan,
        meals,
        daily_calorie_target=daily_calorie_target,
        slot_weights=weights,
        daily_protein_target=daily_protein_target,
    )
    selected = [meal.recipe_index for meal in meals]
    usage = Counter(selected)
    unique_count = len(usage)
    cuisine_usage = Counter(plan.recipes[index].cuisine_type for index in selected)
    protein_usage = Counter(_primary_protein(plan.recipes[index]) for index in selected)
    optimized = plan.model_copy(deep=True)
    optimized.meals = meals
    portion_scales = _calibrate_selected_portions(
        optimized,
        meals,
        daily_calorie_target=daily_calorie_target,
        slot_weights=weights,
    )
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
        portion_scale_by_recipe=portion_scales,
    )
