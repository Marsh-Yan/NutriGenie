"""Deterministic safety and quality validation for AI-generated meal plans."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Iterable

from app.config import settings
from app.services.ai_plan_models import (
    GeneratedPlan,
    GeneratedRecipe,
    NutritionEstimate,
    PlanValidationResult,
    ValidationIssue,
)


ALLERGEN_KEYWORDS = {
    "花生": ("花生", "花生酱"),
    "坚果": ("坚果", "杏仁", "核桃", "腰果", "榛子", "花生"),
    "海鲜": ("虾", "蟹", "贝", "蛤", "鱼", "鱿鱼", "海鲜", "三文鱼", "鳕鱼", "鲈鱼"),
    "鱼": ("鱼", "三文鱼", "鳕鱼", "金枪鱼", "鲈鱼"),
    "乳制品": ("牛奶", "酸奶", "奶酪", "芝士", "黄油", "乳制品"),
    "鸡蛋": ("鸡蛋", "蛋液", "蛋白", "蛋黄"),
    "大豆": ("豆腐", "豆浆", "黄豆", "大豆", "豆制品"),
    "麸质": ("小麦", "面粉", "面包", "面条", "意面", "燕麦", "麸质", "酱油", "生抽", "老抽", "蚝油", "豉油"),
}

VEGAN_BLOCKED = ("鸡", "鸭", "猪", "牛", "羊", "肉", "鱼", "虾", "蟹", "蛋", "奶", "奶酪", "蜂蜜")
GLUTEN_BLOCKED = ("小麦", "面粉", "面包", "面条", "意面", "麸质", "燕麦", "酱油", "生抽", "老抽", "蚝油", "豉油")
KETO_BLOCKED = ("米饭", "面条", "意面", "面包", "馒头", "糖", "砂糖", "藜麦")
MEDICAL_CLAIMS = ("诊断", "治疗", "治愈", "根治", "保证痊愈", "替代药物")


def _zero_nutrition() -> NutritionEstimate:
    return NutritionEstimate(calories=0, protein_g=0, fat_g=0, carbs_g=0, fiber_g=0)


def _nutrition_total(items: Iterable[NutritionEstimate | None]) -> NutritionEstimate:
    values = {key: 0.0 for key in ("calories", "protein_g", "fat_g", "carbs_g", "fiber_g")}
    for item in items:
        if item is None:
            continue
        for key in values:
            values[key] += float(getattr(item, key))
    return NutritionEstimate(**{key: round(value, 2) for key, value in values.items()})


def canonical_recipe_nutrition(recipe: GeneratedRecipe) -> NutritionEstimate:
    return _nutrition_total(item.nutrition_estimate for item in recipe.ingredients)


def canonical_recipe_cost(recipe: GeneratedRecipe) -> float:
    return round(sum(float(item.line_cost_estimate or 0) for item in recipe.ingredients), 2)


def _close_enough(actual: float, declared: float, tolerance: float = 0.2) -> bool:
    return abs(actual - declared) <= max(5.0, abs(declared) * tolerance)


def _allergen_terms(names: Iterable[str]) -> set[str]:
    terms: set[str] = set()
    for name in names:
        raw = str(name).strip().lower()
        if not raw:
            continue
        terms.add(raw)
        terms.update(ALLERGEN_KEYWORDS.get(raw, ()))
    return terms


def _collect_allergens(constraints: dict, intent: dict | None) -> set[str]:
    names = list(constraints.get("allergen_names") or [])
    intent = intent or {}
    concern = intent.get("allergies_or_concerns") or intent.get("allergies")
    if isinstance(concern, str):
        names.extend(part.strip() for part in concern.replace("，", ",").split(","))
    elif isinstance(concern, list):
        names.extend(str(item) for item in concern)
    return _allergen_terms(names)


def _recipe_text(recipe: GeneratedRecipe) -> str:
    return " ".join(
        [recipe.name, recipe.generation_note, *[item.catalog_name or item.name for item in recipe.ingredients], *recipe.steps]
    ).lower()


def _issue(
    issues: list[ValidationIssue],
    code: str,
    message: str,
    severity: str,
    path: str | None = None,
) -> None:
    issues.append(ValidationIssue(code=code, message=message, severity=severity, path=path))


def _minimum_unique(total_meals: int, duration_days: int) -> int:
    return min(total_meals, max(math.ceil(total_meals * settings.PLAN_MIN_UNIQUE_RATIO), duration_days * 2))


def validate_plan(
    plan: GeneratedPlan,
    constraints: dict,
    *,
    intent: dict | None = None,
    duration_days: int,
    require_meals: bool = True,
    require_resolved: bool = False,
    enforce_diversity: bool = False,
    enforce_quality_targets: bool = False,
    normalization_issues: list[dict] | None = None,
) -> PlanValidationResult:
    issues: list[ValidationIssue] = []
    warnings: list[str] = []

    if duration_days < 1 or duration_days > 7:
        _issue(issues, "duration_unsupported", "AI 原生方案目前只支持 1-7 天。", "error")

    recipes = plan.recipes
    if not recipes:
        _issue(issues, "recipes_empty", "未生成任何候选菜品。", "error")

    for item in normalization_issues or []:
        _issue(
            issues,
            item.get("code", "normalization_error"),
            item.get("message", "食材标准化失败"),
            item.get("severity", "error"),
            f"recipes[{item.get('recipe_index', 0)}].ingredients[{item.get('ingredient_index', 0)}]",
        )
        if item.get("severity") == "warning":
            warnings.append(item.get("message", "食材标准化提醒"))

    allergen_terms = _collect_allergens(constraints, intent)
    intent = intent or {}
    diet_type = str(constraints.get("diet_type") or intent.get("diet_type") or "balanced")
    recipe_nutrition: dict[int, NutritionEstimate] = {}
    recipe_cost: dict[int, float] = {}
    names_seen: dict[str, int] = {}

    for index, recipe in enumerate(recipes):
        normalized_name = "".join(recipe.name.lower().split())
        if normalized_name in names_seen:
            _issue(
                issues,
                "duplicate_candidate_name",
                f"候选菜品「{recipe.name}」与另一道候选重复。",
                "error",
                f"recipes[{index}].name",
            )
        else:
            names_seen[normalized_name] = index

        if require_resolved and not recipe.meal_slots:
            _issue(issues, "meal_slots_missing", f"菜品「{recipe.name}」未声明适用餐次。", "error", f"recipes[{index}].meal_slots")

        unresolved = [
            item.name
            for item in recipe.ingredients
            if item.ingredient_id is None or item.nutrition_estimate is None or not item.data_source
        ]
        if require_resolved and unresolved:
            _issue(
                issues,
                "ingredient_unresolved",
                f"菜品「{recipe.name}」仍有未解析食材：{'、'.join(unresolved)}。",
                "error",
                f"recipes[{index}].ingredients",
            )

        recipe_nutrition[index] = canonical_recipe_nutrition(recipe)
        recipe_cost[index] = canonical_recipe_cost(recipe)
        text = _recipe_text(recipe)

        if allergen_terms and any(term in text for term in allergen_terms):
            _issue(issues, "allergen_detected", f"菜品「{recipe.name}」可能包含用户过敏或忌口食材。", "error", f"recipes[{index}]")
        if diet_type == "vegan" and any(term in text for term in VEGAN_BLOCKED):
            _issue(issues, "diet_violation", f"菜品「{recipe.name}」不符合纯素饮食。", "error", f"recipes[{index}]")
        if diet_type == "gluten_free" and any(term in text for term in GLUTEN_BLOCKED):
            _issue(issues, "diet_violation", f"菜品「{recipe.name}」可能含有麸质。", "error", f"recipes[{index}]")
        if diet_type == "keto" and any(term in text for term in KETO_BLOCKED):
            _issue(issues, "diet_violation", f"菜品「{recipe.name}」可能不符合生酮饮食。", "error", f"recipes[{index}]")

        if any(claim in text for claim in MEDICAL_CLAIMS):
            _issue(issues, "medical_claim", f"菜品「{recipe.name}」包含不应出现的医疗化表述。", "error", f"recipes[{index}]")

        actual_nutrition = recipe_nutrition[index]
        declared = recipe.declared_nutrition_estimate
        if declared is not None:
            for key in ("calories", "protein_g", "fat_g", "carbs_g", "fiber_g"):
                if not _close_enough(float(getattr(actual_nutrition, key)), float(getattr(declared, key))):
                    warning = f"菜品「{recipe.name}」的 AI 声明 {key} 与食材目录核算值存在偏差。"
                    warnings.append(warning)
                    _issue(issues, "declared_nutrition_mismatch", warning, "warning", f"recipes[{index}].{key}")
        if recipe.declared_cost_estimate is not None and not _close_enough(recipe_cost[index], recipe.declared_cost_estimate, 0.25):
            warning = f"菜品「{recipe.name}」的 AI 声明成本与食材目录核算值存在偏差。"
            warnings.append(warning)
            _issue(issues, "declared_cost_mismatch", warning, "warning", f"recipes[{index}].cost_estimate")

    if not require_meals:
        has_errors = any(item.severity == "error" for item in issues)
        return PlanValidationResult(
            status="failed" if has_errors else ("warning" if warnings else "passed"),
            passed=not has_errors,
            issues=issues,
            warnings=warnings,
            derived={
                "candidate_count": len(recipes),
                "resolved_ingredient_count": sum(
                    1 for recipe in recipes for item in recipe.ingredients if item.ingredient_id is not None
                ),
            },
        )

    required_slots_by_count = {
        1: {"dinner"},
        2: {"lunch", "dinner"},
        3: {"breakfast", "lunch", "dinner"},
    }
    meal_count = max(1, min(int(intent.get("meal_count_per_day") or 3), 3))
    required_slots = required_slots_by_count[meal_count]
    seen_meals: set[tuple[int, str]] = set()
    daily_totals: dict[int, NutritionEstimate] = defaultdict(_zero_nutrition)
    plan_cost = 0.0
    valid_sequence: list[int] = []

    for meal_index, meal in enumerate(plan.meals):
        key = (meal.day, meal.slot)
        if key in seen_meals:
            _issue(issues, "duplicate_meal_slot", f"第 {meal.day} 天的 {meal.slot} 重复。", "error", f"meals[{meal_index}]")
        seen_meals.add(key)
        if meal.day > duration_days:
            _issue(issues, "day_out_of_range", f"第 {meal.day} 天超出规划天数。", "error", f"meals[{meal_index}]")
        if meal.recipe_index >= len(recipes):
            _issue(issues, "recipe_reference_invalid", f"第 {meal.day} 天引用了不存在的菜品。", "error", f"meals[{meal_index}]")
            continue
        valid_sequence.append(meal.recipe_index)
        nutrition = recipe_nutrition[meal.recipe_index]
        daily = daily_totals[meal.day]
        daily_totals[meal.day] = NutritionEstimate(
            calories=daily.calories + nutrition.calories * meal.servings,
            protein_g=daily.protein_g + nutrition.protein_g * meal.servings,
            fat_g=daily.fat_g + nutrition.fat_g * meal.servings,
            carbs_g=daily.carbs_g + nutrition.carbs_g * meal.servings,
            fiber_g=daily.fiber_g + nutrition.fiber_g * meal.servings,
        )
        plan_cost += recipe_cost[meal.recipe_index] * meal.servings

    for day in range(1, duration_days + 1):
        slots = {slot for day_number, slot in seen_meals if day_number == day}
        for slot in sorted(required_slots - slots):
            _issue(issues, "missing_meal", f"第 {day} 天缺少 {slot}。", "error", f"meals.day_{day}")

    usage = Counter(valid_sequence)
    max_repeat = max(usage.values(), default=0)
    if enforce_diversity and max_repeat > settings.PLAN_MAX_RECIPE_REPEAT:
        _issue(
            issues,
            "recipe_repetition",
            f"同一道菜最多出现 {max_repeat} 次，超过上限 {settings.PLAN_MAX_RECIPE_REPEAT} 次。",
            "error",
        )
    adjacent_duplicates = sum(1 for left, right in zip(valid_sequence, valid_sequence[1:]) if left == right)
    if enforce_diversity and adjacent_duplicates:
        _issue(issues, "adjacent_duplicate", f"存在 {adjacent_duplicates} 个相邻重复餐次。", "error")

    unique_count = len(usage)
    required_unique = _minimum_unique(len(valid_sequence), duration_days)
    if enforce_diversity and valid_sequence and unique_count < required_unique:
        _issue(
            issues,
            "unique_recipe_shortage",
            f"整周只有 {unique_count} 道不同菜品，至少需要 {required_unique} 道。",
            "error",
        )

    days_present = [daily_totals[day] for day in range(1, duration_days + 1)]
    avg_calories = sum(item.calories for item in days_present) / max(1, len(days_present))
    avg_protein = sum(item.protein_g for item in days_present) / max(1, len(days_present))
    calorie_min = float(constraints.get("calorie_min") or 0)
    calorie_max = float(constraints.get("calorie_max") or 0)
    calorie_target = (calorie_min + calorie_max) / 2 if calorie_min and calorie_max else max(calorie_min, calorie_max, 0)
    calorie_deviation = abs(avg_calories - calorie_target) / calorie_target if calorie_target else 0
    if calorie_target and calorie_deviation > settings.PLAN_CALORIE_TOLERANCE:
        message = f"日均热量 {avg_calories:.0f}kcal 偏离目标 {calorie_target:.0f}kcal 达 {calorie_deviation:.0%}。"
        severity = "error" if enforce_quality_targets else "warning"
        _issue(issues, "calorie_target_deviation", message, severity)
        if severity == "warning":
            warnings.append(message)

    target_protein = float(constraints.get("target_protein") or 0)
    if target_protein and avg_protein < target_protein * 0.85:
        warning = f"日均蛋白质 {avg_protein:.1f}g 低于目标 {target_protein:.1f}g。"
        warnings.append(warning)
        _issue(issues, "protein_target_deviation", warning, "warning")

    total_budget = float(constraints.get("total_budget") or 0)
    budget_deviation = (plan_cost - total_budget) / total_budget if total_budget and plan_cost > total_budget else 0
    if total_budget and budget_deviation > settings.PLAN_BUDGET_TOLERANCE:
        message = f"预计成本 {plan_cost:.1f} 元超过总预算 {total_budget:.1f} 元达 {budget_deviation:.0%}。"
        severity = "error" if enforce_quality_targets else "warning"
        _issue(issues, "budget_deviation", message, severity)
        if severity == "warning":
            warnings.append(message)

    has_errors = any(item.severity == "error" for item in issues)
    return PlanValidationResult(
        status="failed" if has_errors else ("warning" if warnings else "passed"),
        passed=not has_errors,
        issues=issues,
        warnings=warnings,
        derived={
            "avg_daily_calories": round(avg_calories, 1),
            "avg_daily_protein_g": round(avg_protein, 1),
            "estimated_plan_cost": round(plan_cost, 2),
            "target_calorie_range": [round(calorie_min, 1), round(calorie_max, 1)],
            "total_budget": round(total_budget, 2),
            "quality_metrics": {
                "meal_count": len(valid_sequence),
                "unique_recipe_count": unique_count,
                "required_unique_count": required_unique,
                "max_recipe_repeat": max_repeat,
                "adjacent_duplicate_count": adjacent_duplicates,
                "calorie_deviation_ratio": round(calorie_deviation, 4),
                "budget_deviation_ratio": round(budget_deviation, 4),
            },
        },
    )
