"""Normalize and aggregate an AI-generated plan without recipe DB lookups."""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import uuid4

from app.config import settings
from app.services.ai_plan_models import GeneratedPlan, NutritionEstimate, PlanValidationResult
from app.services.plan_validator import canonical_recipe_cost, canonical_recipe_nutrition


def _round_nutrition(value: NutritionEstimate) -> dict:
    return {
        "calories": round(value.calories, 1),
        "protein_g": round(value.protein_g, 1),
        "fat_g": round(value.fat_g, 1),
        "carbs_g": round(value.carbs_g, 1),
        "fiber_g": round(value.fiber_g, 1),
    }


def _add_nutrition(left: NutritionEstimate, right: NutritionEstimate, factor: int = 1) -> NutritionEstimate:
    return NutritionEstimate(
        calories=left.calories + right.calories * factor,
        protein_g=left.protein_g + right.protein_g * factor,
        fat_g=left.fat_g + right.fat_g * factor,
        carbs_g=left.carbs_g + right.carbs_g * factor,
        fiber_g=left.fiber_g + right.fiber_g * factor,
    )


def _category_for(name: str) -> str:
    text = name.lower()
    if any(token in text for token in ("肉", "鸡", "鸭", "牛", "猪", "鱼", "虾", "蟹", "豆腐", "蛋")):
        return "蛋白质"
    if any(token in text for token in ("菜", "番茄", "西兰花", "菠菜", "胡萝卜", "菌", "瓜", "椒")):
        return "蔬菜水果"
    if any(token in text for token in ("米", "面", "麦", "藜麦", "燕麦", "土豆")):
        return "主食"
    if any(token in text for token in ("油", "盐", "酱", "醋", "糖", "料酒")):
        return "调味品"
    return "其他"


def _owned(name: str, owned: list[str]) -> bool:
    normalized = name.strip().lower()
    return any(normalized in item.lower() or item.lower() in normalized for item in owned)


def aggregate_generated_plan(
    plan: GeneratedPlan,
    validation: PlanValidationResult,
    *,
    duration_days: int,
    intent: dict | None = None,
    constraints: dict | None = None,
    rag_meta: dict | None = None,
    repair_attempts: int = 0,
    normalization_meta: dict | None = None,
    optimization_meta: dict | None = None,
    ingredient_catalog_version: str = "",
    existing_recipe_keys: dict[int, str] | None = None,
) -> dict:
    draft_id = uuid4().hex[:8]
    all_recipes: list[dict] = []
    recipe_keys: dict[int, str] = {}
    used_recipe_indexes = sorted({
        meal.recipe_index for meal in plan.meals if 0 <= meal.recipe_index < len(plan.recipes)
    })

    for index, recipe in enumerate(plan.recipes):
        recipe_key = (existing_recipe_keys or {}).get(index) or f"generated-{draft_id}-{index + 1}"
        recipe_keys[index] = recipe_key
        canonical_nutrition = canonical_recipe_nutrition(recipe)
        canonical_cost = canonical_recipe_cost(recipe)
        declared_nutrition = recipe.declared_nutrition_estimate or recipe.nutrition_estimate or canonical_nutrition
        declared_cost = recipe.declared_cost_estimate
        all_recipes.append(
            {
                "recipe_key": recipe_key,
                "source": "ai_generated",
                "name": recipe.name,
                "category": recipe.category,
                "cuisine_type": recipe.cuisine_type,
                "difficulty": recipe.difficulty,
                "prep_time_min": recipe.prep_time_min,
                "cook_time_min": recipe.cook_time_min,
                "servings": recipe.servings,
                "meal_slots": recipe.meal_slots,
                "ingredients": [
                    {
                        "ingredient_id": item.ingredient_id or 0,
                        "name": item.name,
                        "input_name": item.input_name or item.name,
                        "catalog_name": item.catalog_name or item.name,
                        "quantity": item.quantity,
                        "unit": item.unit,
                        "estimated_grams": item.estimated_grams,
                        "optional": item.optional,
                        "nutrition_estimate": _round_nutrition(item.nutrition_estimate or NutritionEstimate(calories=0, protein_g=0, fat_g=0, carbs_g=0, fiber_g=0)),
                        "line_cost_estimate": round(item.line_cost_estimate or 0, 2),
                        "resolution_source": item.resolution_source,
                        "data_source": item.data_source or "llm_estimate",
                        "price_known": item.price_known,
                    }
                    for item in recipe.ingredients
                ],
                "steps": recipe.steps,
                "nutrition": _round_nutrition(canonical_nutrition),
                "nutrition_estimate": _round_nutrition(canonical_nutrition),
                "declared_nutrition": _round_nutrition(declared_nutrition),
                "estimated_cost": round(canonical_cost, 2),
                "cost_estimate": round(canonical_cost, 2),
                "declared_cost": round(declared_cost, 2) if declared_cost is not None else None,
                "estimate_source": "ingredient_catalog_v1",
                "generation_note": recipe.generation_note,
            }
        )

    recipes = [all_recipes[index] for index in used_recipe_indexes]
    replacement_pool = [
        item for index, item in enumerate(all_recipes) if index not in used_recipe_indexes
    ]
    recipe_lookup = {item["recipe_key"]: item for item in all_recipes}
    weekly_plan: list[dict] = []
    shopping: dict[str, dict] = {}
    daily_totals: dict[int, NutritionEstimate] = defaultdict(
        lambda: NutritionEstimate(calories=0, protein_g=0, fat_g=0, carbs_g=0, fiber_g=0)
    )
    owned = list((intent or {}).get("owned_ingredients") or [])

    for day in range(1, duration_days + 1):
        day_meals: dict[str, dict] = {}
        for meal in [item for item in plan.meals if item.day == day]:
            recipe_key = recipe_keys.get(meal.recipe_index)
            recipe = recipe_lookup.get(recipe_key or "")
            if not recipe:
                continue
            nutrition = recipe["nutrition"]
            scaled = {
                key: round(float(value) * meal.servings, 1)
                for key, value in nutrition.items()
            }
            day_meals[meal.slot] = {
                "recipe_key": recipe_key,
                "name": recipe["name"],
                "serving_size": meal.servings,
                "nutrition": scaled,
            }
            daily_totals[day] = _add_nutrition(
                daily_totals[day],
                NutritionEstimate(
                    calories=nutrition["calories"],
                    protein_g=nutrition["protein_g"],
                    fat_g=nutrition["fat_g"],
                    carbs_g=nutrition["carbs_g"],
                    fiber_g=nutrition["fiber_g"],
                ),
                meal.servings,
            )
            for ingredient in recipe["ingredients"]:
                if _owned(ingredient["name"], owned):
                    continue
                key = f"{ingredient['name']}::{ingredient['unit']}"
                item = shopping.setdefault(
                    key,
                    {
                        "ingredient_id": ingredient.get("ingredient_id", 0),
                        "name": ingredient["name"],
                        "quantity": 0.0,
                        "unit": ingredient["unit"],
                        "estimated_cost": 0.0,
                        "price_known": True,
                        "price_line_count": 0,
                        "known_price_line_count": 0,
                        "for_recipes": [],
                        "category": _category_for(ingredient["name"]),
                    },
                )
                item["quantity"] += float(ingredient["quantity"]) * meal.servings
                item["estimated_cost"] += float(ingredient["line_cost_estimate"]) * meal.servings
                known_price = ingredient.get("price_known") is True
                item["price_known"] = item["price_known"] and known_price
                item["price_line_count"] += 1
                item["known_price_line_count"] += int(known_price)
                reference = {"recipe_key": recipe_key, "name": recipe["name"]}
                if reference not in item["for_recipes"]:
                    item["for_recipes"].append(reference)
        total = _round_nutrition(daily_totals[day])
        weekly_plan.append({"day": day, "meals": day_meals, "total_nutrition": total})

    shopping_items = []
    by_category: dict[str, list] = defaultdict(list)
    for item in shopping.values():
        item["quantity"] = round(item["quantity"], 2)
        item["estimated_cost"] = round(item["estimated_cost"], 2)
        item.pop("category", None)
        shopping_items.append(item)
        category = _category_for(item["name"])
        by_category[category].append(
            {
                "name": item["name"],
                "quantity": item["quantity"],
                "unit": item["unit"],
                "estimated_cost": item["estimated_cost"],
            }
        )

    total_nutrition = NutritionEstimate(calories=0, protein_g=0, fat_g=0, carbs_g=0, fiber_g=0)
    for day in daily_totals.values():
        total_nutrition = _add_nutrition(total_nutrition, day)
    macro_total = total_nutrition.protein_g * 4 + total_nutrition.fat_g * 9 + total_nutrition.carbs_g * 4
    nutrition_report = {
        "avg_daily_calories": round(total_nutrition.calories / max(1, duration_days), 1),
        "total_calories": round(total_nutrition.calories, 1),
        "protein_g": round(total_nutrition.protein_g / max(1, duration_days), 1),
        "fat_g": round(total_nutrition.fat_g / max(1, duration_days), 1),
        "carbs_g": round(total_nutrition.carbs_g / max(1, duration_days), 1),
        "fiber_g": round(total_nutrition.fiber_g / max(1, duration_days), 1),
        "protein_pct": round(total_nutrition.protein_g * 4 / max(1, macro_total), 3),
        "fat_pct": round(total_nutrition.fat_g * 9 / max(1, macro_total), 3),
        "carbs_pct": round(total_nutrition.carbs_g * 4 / max(1, macro_total), 3),
        "recommendation": "营养和预算由标准食材目录重新核算，实际采购价格可能因地区和时令波动。",
    }

    warnings = list(validation.warnings)
    unique_count = int((optimization_meta or {}).get("unique_recipe_count", 0))
    repeat_count = int((optimization_meta or {}).get("max_recipe_repeat", 0))
    quality_suffix = (
        f"本方案共使用 {unique_count} 道不同菜品，单道菜最多出现 {repeat_count} 次。"
        if unique_count
        else ""
    )
    summary = " ".join(
        part for part in [
            plan.summary or "AI 已生成完整饮食方案。",
            quality_suffix,
            "营养和预算已由标准食材目录重新核算。",
        ] if part
    )
    unknown_price_names = sorted({
        item["name"] for item in shopping_items if not item["price_known"]
    })
    price_line_count = sum(item["price_line_count"] for item in shopping_items)
    price_coverage_ratio = (
        round(sum(item["known_price_line_count"] for item in shopping_items) / price_line_count, 3)
        if price_line_count else 1.0
    )
    unknown_plan_price_names = sorted({
        ingredient["name"] for recipe in recipes for ingredient in recipe["ingredients"]
        if ingredient.get("price_known") is not True
    })
    budget_limit = float((constraints or {}).get("total_budget") or 0)
    known_plan_cost = float(validation.derived.get("estimated_plan_cost") or 0)
    if budget_limit <= 0:
        budget_assessment = "not_set"
    elif known_plan_cost > budget_limit * (1 + settings.PLAN_BUDGET_TOLERANCE):
        budget_assessment = "over_budget"
    elif unknown_plan_price_names:
        budget_assessment = "indeterminate"
    else:
        budget_assessment = "within_budget"
    if unknown_price_names:
        warnings.append("部分食材缺少价格，采购金额仅为已知费用下界，不能据此确认预算达标。")
    if budget_assessment == "indeterminate" and not unknown_price_names:
        warnings.append("计划使用的部分食材缺少价格，无法确认总预算是否达标。")
    result = {
        "schema_version": "ai_native_v2",
        "recipes": recipes,
        "replacement_pool": replacement_pool,
        "weekly_plan": weekly_plan,
        "nutrition_report": nutrition_report,
        "shopping_list": {
            "total_cost": round(sum(item["estimated_cost"] for item in shopping_items), 2),
            "estimated_total_cost_is_lower_bound": bool(unknown_price_names),
            "unknown_price_ingredients": unknown_price_names,
            "price_coverage_ratio": price_coverage_ratio,
            "items": shopping_items,
            "by_category": dict(by_category),
        },
        "validation": {
            **validation.model_dump(mode="json"),
            "status": "warning" if warnings and validation.passed else validation.status,
            "warnings": warnings,
            "budget_assessment": budget_assessment,
            "unknown_price_ingredients": unknown_plan_price_names,
        },
        "generation_meta": {
            "strategy": "ai_native_v2",
            "rag_enabled": bool((rag_meta or {}).get("enabled")),
            "rag_used": bool((rag_meta or {}).get("used")),
            "rag_sources": (rag_meta or {}).get("sources", []),
            "rag_error": (rag_meta or {}).get("error"),
            "repair_attempts": repair_attempts,
            "estimate_source": "ingredient_catalog_v1",
            "nutrition_source": "ingredient_catalog_v1",
            "cost_source": "ingredient_catalog_v1",
            "price_coverage_ratio": price_coverage_ratio,
            "budget_assessment": budget_assessment,
            "ingredient_catalog_version": ingredient_catalog_version,
            "candidate_count": len(plan.recipes),
            "unique_recipe_count": (optimization_meta or {}).get("unique_recipe_count", 0),
            "max_recipe_repeat": (optimization_meta or {}).get("max_recipe_repeat", 0),
            "unresolved_ingredients": (normalization_meta or {}).get("unresolved_ingredients", []),
            "normalization": normalization_meta or {},
            "optimization": optimization_meta or {},
            # Keep the hard-constraint snapshot with the immutable version so
            # later edits can preserve it without re-running intent analysis.
            "intent_snapshot": intent or {},
            "constraints_snapshot": constraints or {},
        },
        "summary": summary,
    }
    return result
