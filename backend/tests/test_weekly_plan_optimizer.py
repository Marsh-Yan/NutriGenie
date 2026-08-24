import pytest

from app.services.ai_plan_models import GeneratedPlan
from app.services.weekly_plan_optimizer import (
    PlanOptimizationError,
    optimize_weekly_plan,
    required_unique_count,
)
from app.services.plan_validator import validate_plan


def _normalized_plan(candidate_count: int) -> GeneratedPlan:
    recipes = []
    for index in range(candidate_count):
        calories = 350 + (index % 5) * 40
        protein = 20 + (index % 4) * 6
        recipes.append(
            {
                "name": f"AI 候选菜 {index + 1}",
                "meal_slots": ["breakfast", "lunch", "dinner"],
                "category": "main_dish",
                "cuisine_type": f"菜系{index % 5}",
                "ingredients": [
                    {
                        "name": "鸡胸肉",
                        "quantity": 100 + index,
                        "unit": "g",
                        "ingredient_id": 3,
                        "catalog_name": "鸡胸肉",
                        "estimated_grams": 100 + index,
                        "nutrition_estimate": {
                            "calories": calories,
                            "protein_g": protein,
                            "fat_g": 10,
                            "carbs_g": 30,
                            "fiber_g": 3,
                        },
                        "line_cost_estimate": 8 + index * 0.1,
                        "resolution_source": "exact",
                        "data_source": "ingredient_catalog_v1",
                    }
                ],
                "steps": ["完成烹饪"],
                "nutrition_estimate": {
                    "calories": calories,
                    "protein_g": protein,
                    "fat_g": 10,
                    "carbs_g": 30,
                    "fiber_g": 3,
                },
                "cost_estimate": 8 + index * 0.1,
            }
        )
    return GeneratedPlan(recipes=recipes)


def _constraints():
    return {
        "calorie_min": 1500,
        "calorie_max": 1800,
        "target_protein": 90,
        "total_budget": 350,
    }


def test_optimizer_enforces_weekly_diversity_and_repeat_limit():
    result = optimize_weekly_plan(
        _normalized_plan(15),
        _constraints(),
        intent={"meal_count_per_day": 3},
        duration_days=7,
    )

    assert result.meal_count == 21
    assert result.unique_recipe_count >= required_unique_count(7, {"meal_count_per_day": 3})
    assert result.max_recipe_repeat <= 2
    assert result.adjacent_duplicate_count == 0
    assert len(result.plan.meals) == 21
    validation = validate_plan(
        result.plan,
        _constraints(),
        intent={"meal_count_per_day": 3},
        duration_days=7,
        require_meals=True,
        require_resolved=True,
        enforce_diversity=True,
        enforce_quality_targets=True,
    )
    assert validation.passed
    assert validation.derived["avg_daily_calories"] == pytest.approx(1650, abs=1)
    assert result.portion_scale_by_recipe


def test_optimizer_rejects_candidate_shortage_instead_of_over_repeating():
    with pytest.raises(PlanOptimizationError) as exc_info:
        optimize_weekly_plan(
            _normalized_plan(7),
            _constraints(),
            intent={"meal_count_per_day": 3},
            duration_days=7,
        )

    assert exc_info.value.feedback["code"] == "candidate_shortage"
