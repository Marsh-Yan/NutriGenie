from app.services.ai_plan_models import GeneratedPlan
from app.services.ingredient_catalog import load_seed_catalog, normalize_generated_plan
from app.services.plan_aggregator import aggregate_generated_plan
from app.services.plan_validator import validate_plan
from app.services.weekly_plan_optimizer import optimize_weekly_plan


def _creative_candidates(count: int = 15) -> GeneratedPlan:
    return GeneratedPlan.model_validate(
        {
            "recipes": [
                {
                    "name": f"番茄创意料理 {index + 1}",
                    "meal_slots": ["breakfast", "lunch", "dinner"],
                    "category": "light_meal" if index % 2 else "main_dish",
                    "cuisine_type": f"风格{index % 5}",
                    "difficulty": "easy",
                    "ingredients": [
                        {"name": "西红柿", "quantity": 120 + index * 5, "unit": "g"},
                        {"name": "鸡蛋", "quantity": 1, "unit": "个"},
                    ],
                    "steps": ["处理标准食材", "完成烹饪并装盘"],
                    "generation_note": "由 AI 即时创作",
                }
                for index in range(count)
            ],
            "meals": [],
            "summary": "使用标准食材创作的多样化方案。",
        }
    )


def test_v2_pipeline_recalculates_facts_and_builds_diverse_week():
    constraints = {
        "diet_type": "balanced",
        "allergen_names": [],
        "calorie_min": 0,
        "calorie_max": 0,
        "target_protein": 0,
        "total_budget": 0,
    }
    intent = {"meal_count_per_day": 3}
    normalized = normalize_generated_plan(_creative_candidates(), load_seed_catalog())
    candidate_validation = validate_plan(
        normalized.plan,
        constraints,
        intent=intent,
        duration_days=7,
        require_meals=False,
        require_resolved=True,
        normalization_issues=[item.model_dump(mode="json") for item in normalized.issues],
    )
    assert candidate_validation.passed is True
    assert normalized.unresolved_ingredients == []

    optimized = optimize_weekly_plan(
        normalized.plan,
        constraints,
        intent=intent,
        duration_days=7,
    )
    final_validation = validate_plan(
        optimized.plan,
        constraints,
        intent=intent,
        duration_days=7,
        require_meals=True,
        require_resolved=True,
        enforce_diversity=True,
        enforce_quality_targets=True,
        normalization_issues=[item.model_dump(mode="json") for item in normalized.issues],
    )
    assert final_validation.passed is True

    result = aggregate_generated_plan(
        optimized.plan,
        final_validation,
        duration_days=7,
        intent=intent,
        constraints=constraints,
        normalization_meta={
            "catalog_version": normalized.catalog_version,
            "unresolved_ingredients": normalized.unresolved_ingredients,
        },
        optimization_meta=optimized.model_dump(mode="json", exclude={"plan"}),
        ingredient_catalog_version=normalized.catalog_version,
    )

    assert result["schema_version"] == "ai_native_v2"
    assert len(result["weekly_plan"]) == 7
    assert len(result["recipes"]) == result["generation_meta"]["unique_recipe_count"]
    assert result["generation_meta"]["unique_recipe_count"] >= 15
    assert result["generation_meta"]["max_recipe_repeat"] <= 2
    assert result["generation_meta"]["unresolved_ingredients"] == []
    assert result["recipes"][0]["ingredients"][0]["data_source"] == "ingredient_catalog_v1"
    assert result["recipes"][0]["ingredients"][0]["input_name"] == "西红柿"
