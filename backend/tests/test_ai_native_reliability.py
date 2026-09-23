import asyncio
import json

from app.services import ai_plan_generator
from app.services.ai_plan_models import GeneratedPlan
from app.services.ingredient_catalog import load_seed_catalog, normalize_generated_plan
from app.services.meal_replacement import replace_meal_in_snapshot
from app.services.plan_aggregator import aggregate_generated_plan
from app.services.plan_validator import validate_plan
from app.services.weekly_plan_optimizer import optimize_weekly_plan


def _candidate_plan(count=8):
    return GeneratedPlan.model_validate({"recipes": [
        {
            "name": f"番茄鸡蛋餐 {index}",
            "meal_slots": ["breakfast", "lunch", "dinner"],
            "ingredients": [
                {"name": "番茄", "quantity": 100 + index * 5, "unit": "g"},
                {"name": "鸡蛋", "quantity": 1, "unit": "个"},
            ],
            "steps": ["处理食材", "烹饪后装盘"],
        }
        for index in range(count)
    ]})


def test_truncated_model_output_retries_with_fewer_candidates(monkeypatch):
    prompts = []

    async def fake_invoke(prompt, *, temperature):
        prompts.append(json.loads(prompt))
        if len(prompts) == 1:
            raise ai_plan_generator.PlanGenerationError("LLM 输出达到长度上限，结构化餐单未完整返回")
        return _candidate_plan()

    monkeypatch.setattr(ai_plan_generator, "_invoke_plan", fake_invoke)
    plan = asyncio.run(ai_plan_generator.generate_plan(
        user_input="一周三餐", constraints={}, candidate_target=28,
    ))
    assert len(plan.recipes) == 8
    assert [item["candidate_target"] for item in prompts] == [28, 19]


def test_daily_protein_shortfall_fails_final_quality_gate():
    raw = _candidate_plan(3).model_dump(mode="json")
    raw["meals"] = [
        {"day": 1, "slot": slot, "recipe_index": index, "servings": 1}
        for index, slot in enumerate(("breakfast", "lunch", "dinner"))
    ]
    plan = GeneratedPlan.model_validate(raw)
    result = validate_plan(
        plan,
        {"target_protein": 140, "calorie_min": 0, "calorie_max": 0, "total_budget": 0},
        intent={"meal_count_per_day": 3}, duration_days=1,
        enforce_quality_targets=True,
    )
    assert not result.passed
    assert result.derived["low_protein_days"] == [1]
    assert any(issue.code == "daily_protein_target_deviation" for issue in result.issues)


def test_fractional_egg_portion_is_visible_as_practicality_warning():
    raw = _candidate_plan(1).model_dump(mode="json")
    raw["recipes"][0]["ingredients"][1]["quantity"] = 3.23
    raw["meals"] = [{"day": 1, "slot": "dinner", "recipe_index": 0}]
    result = validate_plan(
        GeneratedPlan.model_validate(raw), {},
        intent={"meal_count_per_day": 1}, duration_days=1,
    )
    assert result.status == "warning"
    assert any(issue.code == "portion_practicality" for issue in result.issues)


def test_missing_price_makes_budget_indeterminate():
    source = normalize_generated_plan(_candidate_plan(3), load_seed_catalog()).plan
    normalized = GeneratedPlan.model_validate({
        **source.model_dump(mode="json"),
        "meals": [
            {"day": 1, "slot": slot, "recipe_index": index}
            for index, slot in enumerate(("breakfast", "lunch", "dinner"))
        ],
    })
    for recipe in normalized.recipes:
        for ingredient in recipe.ingredients:
            ingredient.price_known = True
    normalized.recipes[0].ingredients[0].price_known = False
    constraints = {"total_budget": 1000}
    validation = validate_plan(normalized, constraints, duration_days=1)
    result = aggregate_generated_plan(normalized, validation, duration_days=1, constraints=constraints)
    assert result["validation"]["budget_assessment"] == "indeterminate"
    assert result["validation"]["status"] == "warning"
    assert result["shopping_list"]["estimated_total_cost_is_lower_bound"] is True


def test_one_day_replacement_uses_reserve_and_preserves_other_meals():
    constraints = {
        "diet_type": "balanced", "allergen_names": [], "calorie_min": 0,
        "calorie_max": 0, "target_protein": 0, "total_budget": 0,
    }
    intent = {"meal_count_per_day": 3}
    normalized = normalize_generated_plan(_candidate_plan(), load_seed_catalog())
    optimized = optimize_weekly_plan(normalized.plan, constraints, intent=intent, duration_days=1)
    validation = validate_plan(
        optimized.plan, constraints, intent=intent, duration_days=1,
        require_resolved=True, enforce_diversity=True, enforce_quality_targets=True,
    )
    assert validation.passed
    original = aggregate_generated_plan(
        optimized.plan, validation, duration_days=1, intent=intent,
        constraints=constraints,
    )
    assert len(original["replacement_pool"]) == 5
    before = original["weekly_plan"][0]["meals"]
    reserve_keys = {item["recipe_key"] for item in original["replacement_pool"]}
    replaced = replace_meal_in_snapshot(
        original, day=1, slot="lunch", reason="other", excluded_ids=[],
        excluded_keys=[], duration_days=1, profile_allergies=[],
        profile_diet_type="balanced", total_budget=0,
    )
    assert replaced is not None
    after = replaced["weekly_plan"][0]["meals"]
    assert after["lunch"]["recipe_key"] in reserve_keys
    assert after["breakfast"]["recipe_key"] == before["breakfast"]["recipe_key"]
    assert after["dinner"]["recipe_key"] == before["dinner"]["recipe_key"]
    assert len(replaced["replacement_pool"]) == 5
