from app.services.ai_plan_models import GeneratedPlan
from app.services.ingredient_catalog import (
    CATALOG_SOURCE,
    CatalogIngredient,
    build_catalog,
    load_seed_catalog,
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


def test_seed_catalog_contains_expanded_ingredient_facts():
    catalog = load_seed_catalog()
    names = {item.name for item in catalog.entries}

    assert len(catalog.entries) >= 130
    assert len({item.ingredient_id for item in catalog.entries}) == len(catalog.entries)
    assert {"水", "糙米", "藜麦", "鸡翅", "鲫鱼", "鹰嘴豆", "苹果", "杏仁", "菜籽油"} <= names


def test_water_and_common_water_alias_are_resolved():
    catalog = load_seed_catalog()

    exact = normalize_generated_plan(_plan(name="水", unit="ml"), catalog)
    alias = normalize_generated_plan(_plan(name="清水", unit="ml"), catalog)

    assert exact.unresolved_ingredients == []
    assert exact.plan.recipes[0].ingredients[0].estimated_grams == 200
    assert exact.plan.recipes[0].ingredients[0].nutrition_estimate.calories == 0
    assert alias.unresolved_ingredients == []
    assert alias.plan.recipes[0].ingredients[0].name == "水"
    assert alias.plan.recipes[0].ingredients[0].resolution_source == "alias"
