"""Deterministic replacement from already-validated AI recipes.

No LLM or unsafe catalog fallback is used. Every candidate is rechecked against
the saved hard constraints and whole-plan nutrition, budget, and diversity.
"""

from __future__ import annotations

from copy import deepcopy

from app.services.ai_plan_models import GeneratedPlan
from app.services.plan_aggregator import aggregate_generated_plan
from app.services.plan_validator import validate_plan


def replace_meal_in_snapshot(
    result: dict,
    *,
    day: int,
    slot: str,
    reason: str,
    excluded_ids: list[int],
    excluded_keys: list[str],
    duration_days: int,
    profile_allergies: list[str],
    profile_diet_type: str,
    total_budget: float,
) -> dict | None:
    if result.get("schema_version") != "ai_native_v2":
        return None
    source_recipes = (result.get("recipes") or []) + (result.get("replacement_pool") or [])
    source_days = result.get("weekly_plan") or []
    target_day = next((item for item in source_days if item.get("day") == day), None)
    current = (target_day or {}).get("meals", {}).get(slot)
    if not current or not current.get("recipe_key"):
        return None
    recipe_keys = [item.get("recipe_key") for item in source_recipes]
    if any(not key for key in recipe_keys) or len(set(recipe_keys)) != len(recipe_keys):
        return None
    current_index = recipe_keys.index(current["recipe_key"]) if current["recipe_key"] in recipe_keys else -1
    if current_index < 0:
        return None
    meals = []
    for plan_day in source_days:
        for meal_slot, meal in (plan_day.get("meals") or {}).items():
            key = meal.get("recipe_key")
            if key not in recipe_keys:
                return None
            meals.append({
                "day": plan_day["day"], "slot": meal_slot,
                "recipe_index": recipe_keys.index(key),
                "servings": meal.get("serving_size", 1),
            })
    recipes = []
    for item in source_recipes:
        if any(
            int(ingredient.get("ingredient_id") or 0) <= 0
            or ingredient.get("data_source") != "ingredient_catalog_v1"
            for ingredient in item.get("ingredients") or []
        ):
            return None
        recipe = deepcopy(item)
        recipe["nutrition_estimate"] = item.get("nutrition")
        recipe["cost_estimate"] = item.get("estimated_cost")
        recipes.append(recipe)

    meta = result.get("generation_meta") or {}
    if not isinstance(meta.get("intent_snapshot"), dict) or not isinstance(meta.get("constraints_snapshot"), dict):
        return None
    intent = dict(meta.get("intent_snapshot") or {})
    constraints = dict(meta.get("constraints_snapshot") or {})
    # Never rely solely on old snapshots when the current profile is stricter.
    constraints["allergen_names"] = sorted(set(constraints.get("allergen_names") or []) | set(profile_allergies or []))
    if profile_diet_type in ("vegan", "gluten_free", "keto"):
        constraints["diet_type"] = profile_diet_type
    constraints["total_budget"] = total_budget

    candidates = []
    current_recipe = source_recipes[current_index]
    difficulty_rank = {"easy": 0, "medium": 1, "hard": 2}
    current_time = int(current_recipe.get("prep_time_min") or 0) + int(current_recipe.get("cook_time_min") or 0)
    for index, recipe in enumerate(source_recipes):
        if index == current_index or recipe.get("recipe_key") in excluded_keys or recipe.get("recipe_id") in excluded_ids:
            continue
        slots = recipe.get("meal_slots") or []
        if slots and slot not in slots:
            continue
        if reason == "too_expensive" and float(recipe.get("estimated_cost") or 0) >= float(current_recipe.get("estimated_cost") or 0):
            continue
        if reason == "too_slow" and int(recipe.get("prep_time_min") or 0) + int(recipe.get("cook_time_min") or 0) >= current_time:
            continue
        if reason == "too_difficult" and difficulty_rank.get(recipe.get("difficulty"), 3) >= difficulty_rank.get(current_recipe.get("difficulty"), 3):
            continue
        candidates.append(index)
    if reason == "too_expensive":
        candidates.sort(key=lambda index: float(source_recipes[index].get("estimated_cost") or 0))
    elif reason == "too_slow":
        candidates.sort(key=lambda index: int(source_recipes[index].get("prep_time_min") or 0) + int(source_recipes[index].get("cook_time_min") or 0))
    elif reason == "too_difficult":
        candidates.sort(key=lambda index: difficulty_rank.get(source_recipes[index].get("difficulty"), 3))

    for index in candidates:
        variant_meals = deepcopy(meals)
        for meal in variant_meals:
            if meal["day"] == day and meal["slot"] == slot:
                meal["recipe_index"] = index
                break
        try:
            candidate = GeneratedPlan.model_validate({"recipes": recipes, "meals": variant_meals, "summary": result.get("summary", "")[:2000]})
            validation = validate_plan(
                candidate, constraints, intent=intent, duration_days=duration_days,
                require_meals=True, require_resolved=True,
                enforce_diversity=True, enforce_quality_targets=True,
            )
        except (ValueError, TypeError):
            continue
        if not validation.passed:
            continue
        quality = validation.derived.get("quality_metrics") or {}
        aggregated = aggregate_generated_plan(
            candidate, validation, duration_days=duration_days,
            intent=intent, constraints=constraints,
            rag_meta={
                "enabled": meta.get("rag_enabled", False),
                "used": meta.get("rag_used", False),
                "sources": meta.get("rag_sources", []),
                "error": meta.get("rag_error"),
            },
            repair_attempts=int(meta.get("repair_attempts") or 0),
            normalization_meta=meta.get("normalization") or {},
            optimization_meta={
                **(meta.get("optimization") or {}),
                "unique_recipe_count": quality.get("unique_recipe_count", 0),
                "max_recipe_repeat": quality.get("max_recipe_repeat", 0),
            },
            ingredient_catalog_version=meta.get("ingredient_catalog_version") or "",
            existing_recipe_keys={i: key for i, key in enumerate(recipe_keys)},
        )
        return aggregated
    return None
