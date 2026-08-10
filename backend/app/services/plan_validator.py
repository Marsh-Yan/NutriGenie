"""Deterministic validation for LLM-generated meal plans."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app.services.ai_plan_models import (
    GeneratedPlan,
    GeneratedRecipe,
    NutritionEstimate,
    PlanValidationResult,
    ValidationIssue,
)


ALLERGEN_KEYWORDS = {
    "花生": ("花生", "花生酱"),
    "坚果": ("坚果", "杏仁", "核桃", "腰果", "榛子"),
    "海鲜": ("虾", "蟹", "贝", "蛤", "鱼", "鱿鱼", "海鲜", "三文鱼"),
    "鱼": ("鱼", "三文鱼", "鳕鱼", "金枪鱼"),
    "乳制品": ("牛奶", "酸奶", "奶酪", "芝士", "黄油", "乳制品"),
    "鸡蛋": ("鸡蛋", "蛋液", "蛋白", "蛋黄"),
    "大豆": ("豆腐", "豆浆", "黄豆", "大豆", "豆制品"),
    "麸质": ("小麦", "面粉", "面包", "面条", "意面", "燕麦", "麸质"),
}

VEGAN_BLOCKED = ("鸡", "鸭", "猪", "牛", "羊", "肉", "鱼", "虾", "蟹", "蛋", "奶", "奶酪", "蜂蜜")
GLUTEN_BLOCKED = ("小麦", "面粉", "面包", "面条", "意面", "麸质", "燕麦")
KETO_BLOCKED = ("米饭", "面条", "意面", "面包", "馒头", "糖", "砂糖", "藜麦")
MEDICAL_CLAIMS = ("诊断", "治疗", "治愈", "根治", "保证痊愈", "替代药物")


def _nutrition_total(items: Iterable[NutritionEstimate]) -> NutritionEstimate:
    values = {key: 0.0 for key in ("calories", "protein_g", "fat_g", "carbs_g", "fiber_g")}
    for item in items:
        for key in values:
            values[key] += float(getattr(item, key))
    return NutritionEstimate(**{key: round(value, 1) for key, value in values.items()})


def canonical_recipe_nutrition(recipe: GeneratedRecipe) -> NutritionEstimate:
    return _nutrition_total(item.nutrition_estimate for item in recipe.ingredients)


def canonical_recipe_cost(recipe: GeneratedRecipe) -> float:
    return round(sum(float(item.line_cost_estimate) for item in recipe.ingredients), 2)


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
        [recipe.name, recipe.generation_note, *[item.name for item in recipe.ingredients], *recipe.steps]
    ).lower()


def _issue(issues: list[ValidationIssue], code: str, message: str, severity: str, path: str | None = None) -> None:
    issues.append(ValidationIssue(code=code, message=message, severity=severity, path=path))


def validate_plan(
    plan: GeneratedPlan,
    constraints: dict,
    *,
    intent: dict | None = None,
    duration_days: int,
) -> PlanValidationResult:
    issues: list[ValidationIssue] = []
    warnings: list[str] = []

    if duration_days < 1 or duration_days > 7:
        _issue(issues, "duration_unsupported", "AI 原生方案目前只支持 1-7 天。", "error")

    recipes = plan.recipes
    if not recipes:
        _issue(issues, "recipes_empty", "未生成任何菜谱。", "error")

    allergen_terms = _collect_allergens(constraints, intent)
    intent = intent or {}
    diet_type = str(constraints.get("diet_type") or intent.get("diet_type") or "balanced")
    recipe_nutrition: dict[int, NutritionEstimate] = {}
    recipe_cost: dict[int, float] = {}

    for index, recipe in enumerate(recipes):
        recipe_nutrition[index] = canonical_recipe_nutrition(recipe)
        recipe_cost[index] = canonical_recipe_cost(recipe)
        text = _recipe_text(recipe)

        if allergen_terms and any(term in text for term in allergen_terms):
            _issue(issues, "allergen_detected", f"菜谱「{recipe.name}」可能包含用户过敏或忌口食材。", "error", f"recipes[{index}]")

        if diet_type == "vegan" and any(term in text for term in VEGAN_BLOCKED):
            _issue(issues, "diet_violation", f"菜谱「{recipe.name}」不符合纯素饮食。", "error", f"recipes[{index}]")
        if diet_type == "gluten_free" and any(term in text for term in GLUTEN_BLOCKED):
            _issue(issues, "diet_violation", f"菜谱「{recipe.name}」可能含有麸质。", "error", f"recipes[{index}]")
        if diet_type == "keto" and any(term in text for term in KETO_BLOCKED):
            _issue(issues, "diet_violation", f"菜谱「{recipe.name}」可能不符合生酮饮食。", "error", f"recipes[{index}]")

        for claim in MEDICAL_CLAIMS:
            if claim in text:
                _issue(issues, "medical_claim", f"菜谱「{recipe.name}」包含不应出现的医疗化表述。", "error", f"recipes[{index}]")
                break

        actual_nutrition = recipe_nutrition[index]
        declared = recipe.nutrition_estimate
        for key in ("calories", "protein_g", "fat_g", "carbs_g", "fiber_g"):
            actual = float(getattr(actual_nutrition, key))
            expected = float(getattr(declared, key))
            if not _close_enough(actual, expected):
                warnings.append(f"菜谱「{recipe.name}」的 {key} 与食材行项目汇总存在偏差。")
                _issue(issues, "nutrition_mismatch", warnings[-1], "warning", f"recipes[{index}].nutrition_estimate.{key}")
        if not _close_enough(recipe_cost[index], recipe.cost_estimate, 0.25):
            warning = f"菜谱「{recipe.name}」的成本与食材成本汇总存在偏差。"
            warnings.append(warning)
            _issue(issues, "cost_mismatch", warning, "warning", f"recipes[{index}].cost_estimate")

        macro_calories = actual_nutrition.protein_g * 4 + actual_nutrition.carbs_g * 4 + actual_nutrition.fat_g * 9
        if actual_nutrition.calories and not _close_enough(macro_calories, actual_nutrition.calories, 0.3):
            warning = f"菜谱「{recipe.name}」的宏量营养素与热量估算不完全一致。"
            warnings.append(warning)
            _issue(issues, "macro_calorie_mismatch", warning, "warning", f"recipes[{index}]")

    required_slots = {"breakfast", "lunch", "dinner"}
    seen_meals: set[tuple[int, str]] = set()
    daily_totals: dict[int, NutritionEstimate] = defaultdict(lambda: NutritionEstimate(calories=0, protein_g=0, fat_g=0, carbs_g=0, fiber_g=0))
    plan_cost = 0.0

    for meal_index, meal in enumerate(plan.meals):
        key = (meal.day, meal.slot)
        if key in seen_meals:
            _issue(issues, "duplicate_meal_slot", f"第 {meal.day} 天的 {meal.slot} 重复。", "error", f"meals[{meal_index}]")
        seen_meals.add(key)
        if meal.day > duration_days:
            _issue(issues, "day_out_of_range", f"第 {meal.day} 天超出规划天数。", "error", f"meals[{meal_index}]")
        if meal.recipe_index >= len(recipes):
            _issue(issues, "recipe_reference_invalid", f"第 {meal.day} 天引用了不存在的菜谱。", "error", f"meals[{meal_index}]")
            continue
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
            _issue(issues, "missing_meal", f"第 {day} 天缺少{slot}。", "error", f"meals.day_{day}")

    days_present = [daily_totals[day] for day in range(1, duration_days + 1)]
    avg_calories = sum(item.calories for item in days_present) / max(1, len(days_present))
    avg_protein = sum(item.protein_g for item in days_present) / max(1, len(days_present))
    calorie_min = float(constraints.get("calorie_min") or 0)
    calorie_max = float(constraints.get("calorie_max") or 0)
    if calorie_min and (avg_calories < calorie_min or avg_calories > calorie_max):
        warning = f"日均热量 {avg_calories:.0f}kcal 偏离目标范围 {calorie_min:.0f}-{calorie_max:.0f}kcal。"
        warnings.append(warning)
        _issue(issues, "calorie_target_deviation", warning, "warning")

    target_protein = float(constraints.get("target_protein") or 0)
    if target_protein and avg_protein < target_protein * 0.85:
        warning = f"日均蛋白质 {avg_protein:.1f}g 低于目标 {target_protein:.1f}g。"
        warnings.append(warning)
        _issue(issues, "protein_target_deviation", warning, "warning")

    total_budget = float(constraints.get("total_budget") or 0)
    if total_budget and plan_cost > total_budget:
        warning = f"预计成本 {plan_cost:.1f} 元超过总预算 {total_budget:.1f} 元。"
        warnings.append(warning)
        _issue(issues, "budget_deviation", warning, "warning")

    repeated = [index for index in range(len(recipes)) if sum(1 for meal in plan.meals if meal.recipe_index == index) > 3]
    if repeated:
        warning = f"有 {len(repeated)} 道菜一周出现超过 3 次。"
        warnings.append(warning)
        _issue(issues, "recipe_repetition", warning, "warning")

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
        },
    )
