from app.services.ai_plan_models import GeneratedPlan
from app.services.ingredient_catalog import (
    CATALOG_SOURCE,
    CatalogIngredient,
    build_catalog,
    normalize_generated_plan,
    strict_grams,
)


def _catalog():
    return build_catalog(
        [
            CatalogIngredient(
                ingredient_id=1,
                name="番茄",
                category="vegetable",
                unit="个",
                unit_price=2.5,
                calories_per_100g=18,
                protein_per_100g=0.9,
                fat_per_100g=0.2,
                carbs_per_100g=3.9,
                fiber_per_100g=1.2,
            )
        ]
    )


def _plan(name: str = "西红柿", unit: str = "g") -> GeneratedPlan:
    return GeneratedPlan.model_validate(
        {
            "recipes": [
                {
                    "name": "清爽番茄",
                    "meal_slots": ["breakfast"],
                    "ingredients": [{"name": name, "quantity": 200, "unit": unit}],
                    "steps": ["切块后装盘"],
                }
            ]
        }
    )


def test_alias_is_resolved_and_facts_are_recalculated():
    result = normalize_generated_plan(_plan(), _catalog())
    item = result.plan.recipes[0].ingredients[0]

    assert result.unresolved_ingredients == []
    assert item.name == "番茄"
    assert item.input_name == "西红柿"
    assert item.resolution_source == "alias"
    assert item.data_source == CATALOG_SOURCE
    assert item.estimated_grams == 200
    assert item.nutrition_estimate.calories == 36
    assert item.line_cost_estimate == 3.33
    assert result.plan.recipes[0].nutrition_estimate.calories == 36


def test_unknown_ingredient_is_a_hard_normalization_issue():
    result = normalize_generated_plan(_plan(name="火星蔬菜"), _catalog())

    assert result.unresolved_ingredients == ["火星蔬菜"]
    assert result.issues[0].code == "ingredient_unresolved"
    assert result.issues[0].severity == "error"


def test_unknown_unit_does_not_silently_fall_back_to_one_gram():
    result = normalize_generated_plan(_plan(unit="适量"), _catalog())

    assert result.issues[0].code == "unit_unresolved"
    assert result.issues[0].severity == "error"


def test_category_specific_unit_conversion_is_deterministic():
    assert strict_grams(2, "个", "vegetable") == 300
