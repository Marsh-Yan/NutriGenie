"""Tests for the database-independent AI-native plan core."""

from app.services.ai_plan_models import GeneratedPlan
from app.services.plan_aggregator import aggregate_generated_plan
from app.services.plan_validator import validate_plan


def sample_plan() -> GeneratedPlan:
    return GeneratedPlan.model_validate(
        {
            "recipes": [
                {
                    "name": "番茄鸡胸肉碗",
                    "category": "main_dish",
                    "cuisine_type": "家常",
                    "difficulty": "easy",
                    "prep_time_min": 10,
                    "cook_time_min": 15,
                    "servings": 1,
                    "ingredients": [
                        {
                            "name": "鸡胸肉",
                            "quantity": 150,
                            "unit": "g",
                            "nutrition_estimate": {
                                "calories": 165,
                                "protein_g": 34,
                                "fat_g": 3,
                                "carbs_g": 0,
                                "fiber_g": 0,
                            },
                            "line_cost_estimate": 8,
                        },
                        {
                            "name": "番茄",
                            "quantity": 200,
                            "unit": "g",
                            "nutrition_estimate": {
                                "calories": 36,
                                "protein_g": 2,
                                "fat_g": 0,
                                "carbs_g": 8,
                                "fiber_g": 2,
                            },
                            "line_cost_estimate": 3,
                        },
                    ],
                    "steps": ["切配食材", "煎熟鸡胸肉并与番茄组合"],
                    "nutrition_estimate": {
                        "calories": 201,
                        "protein_g": 36,
                        "fat_g": 3,
                        "carbs_g": 8,
                        "fiber_g": 2,
                    },
                    "cost_estimate": 11,
                    "generation_note": "高蛋白、简单易做",
                }
            ],
            "meals": [
                {"day": 1, "slot": "breakfast", "recipe_index": 0, "servings": 1},
                {"day": 1, "slot": "lunch", "recipe_index": 0, "servings": 1},
                {"day": 1, "slot": "dinner", "recipe_index": 0, "servings": 1},
            ],
            "summary": "以高蛋白和简单烹饪为主。",
        }
    )


def constraints():
    return {
        "diet_type": "balanced",
        "health_goal": "healthy",
        "allergen_names": [],
        "calorie_min": 500,
        "calorie_max": 1000,
        "target_protein": 30,
        "total_budget": 50,
    }


def test_valid_plan_passes_without_database():
    result = validate_plan(sample_plan(), constraints(), duration_days=1)
    assert result.passed is True
    assert result.status in {"passed", "warning"}
    assert result.derived["estimated_plan_cost"] == 33


def test_allergen_is_hard_error():
    result = validate_plan(
        sample_plan(),
        {**constraints(), "allergen_names": ["鸡蛋"]},
        duration_days=1,
        intent={"allergies_or_concerns": "鸡胸肉"},
    )
    assert result.passed is False
    assert any(issue.code == "allergen_detected" for issue in result.issues)


def test_gluten_free_rejects_uncertified_soy_sauce():
    plan = sample_plan()
    plan.recipes[0].ingredients[1].name = "酱油"
    result = validate_plan(
        plan,
        {**constraints(), "diet_type": "gluten_free"},
        duration_days=1,
    )
    assert result.passed is False
    assert any(issue.code == "diet_violation" for issue in result.issues)


def test_gluten_free_rejects_unlisted_sauce_in_steps():
    plan = sample_plan()
    plan.recipes[0].steps.append("淋上蒸鱼豉油")
    result = validate_plan(
        plan,
        {**constraints(), "diet_type": "gluten_free"},
        duration_days=1,
    )
    assert result.passed is False
    assert any(issue.code == "diet_violation" for issue in result.issues)


def test_aggregator_creates_generated_keys_and_shopping_list():
    plan = sample_plan()
    validation = validate_plan(plan, constraints(), duration_days=1)
    result = aggregate_generated_plan(
        plan,
        validation,
        duration_days=1,
        intent={"owned_ingredients": ["番茄"]},
        constraints=constraints(),
        rag_meta={"enabled": False, "used": False},
    )
    assert result["schema_version"] == "ai_native_v2"
    assert result["recipes"][0]["recipe_key"].startswith("generated-")
    assert result["weekly_plan"][0]["meals"]["lunch"]["recipe_key"] == result["recipes"][0]["recipe_key"]
    assert [item["name"] for item in result["shopping_list"]["items"]] == ["鸡胸肉"]
    assert result["nutrition_report"]["avg_daily_calories"] == 603
    assert result["generation_meta"]["constraints_snapshot"]["diet_type"] == "balanced"
    assert result["generation_meta"]["nutrition_source"] == "ingredient_catalog_v1"


def test_aggregator_reports_daily_macros_for_multi_day_plan():
    plan = sample_plan()
    plan.meals.extend([meal.model_copy(update={"day": 2}) for meal in list(plan.meals)])
    validation = validate_plan(plan, constraints(), duration_days=2)
    result = aggregate_generated_plan(plan, validation, duration_days=2, constraints=constraints())

    report = result["nutrition_report"]
    assert report["total_calories"] == 1206
    assert report["avg_daily_calories"] == 603
    assert report["protein_g"] == 108
    assert report["fat_g"] == 9
    assert report["carbs_g"] == 24
    assert report["fiber_g"] == 6
