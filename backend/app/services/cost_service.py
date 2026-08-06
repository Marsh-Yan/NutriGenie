"""Ingredient quantity and cost conversion helpers.

Recipe quantities and market prices intentionally use different units (for
example, a recipe may use 300g chicken while the market price is per 斤).
All cost callers must go through this module instead of multiplying the two
numbers directly.
"""

from __future__ import annotations

from typing import Dict


# Approximate reference weights/volumes. They are used only to bridge a recipe
# unit and its purchase/pricing unit; exact matching units retain their value.
UNIT_TO_REFERENCE: Dict[str, float] = {
    "g": 1.0, "克": 1.0,
    "kg": 1000.0, "公斤": 1000.0, "千克": 1000.0,
    "斤": 500.0, "两": 50.0,
    "ml": 1.0, "毫升": 1.0,
    "L": 1000.0, "升": 1000.0,
    "个": 50.0, "颗": 100.0, "根": 100.0, "条": 200.0,
    "块": 200.0, "片": 20.0, "盒": 200.0, "包": 200.0,
    "瓶": 500.0, "罐": 200.0, "袋": 500.0, "把": 200.0,
}

CATEGORY_UNIT_TO_REFERENCE: Dict[str, Dict[str, float]] = {
    "vegetable": {"个": 150.0, "颗": 200.0, "根": 80.0, "把": 200.0},
    "fruit": {"个": 150.0, "颗": 20.0, "片": 30.0},
    "meat": {"块": 200.0, "片": 50.0, "条": 100.0},
    "seafood": {"个": 30.0, "条": 200.0},
    "egg": {"个": 50.0, "颗": 50.0},
    "dairy": {"盒": 250.0, "瓶": 250.0, "片": 20.0},
    "grain": {"碗": 200.0, "包": 500.0, "片": 80.0},
    "condiment": {"勺": 15.0, "汤匙": 15.0, "茶匙": 5.0, "瓶": 500.0},
}

DISCRETE_PURCHASE_UNITS = {
    "个", "颗", "根", "条", "块", "片", "盒", "包", "瓶", "罐", "袋", "把",
}


def unit_to_reference(unit: str, category: str = "other") -> float:
    """Return the reference size of one unit, using category-specific values."""
    return CATEGORY_UNIT_TO_REFERENCE.get(category, {}).get(
        unit, UNIT_TO_REFERENCE.get(unit, 1.0)
    )


def convert_quantity(
    quantity: float,
    from_unit: str,
    to_unit: str,
    category: str = "other",
) -> float:
    """Convert a recipe quantity into the ingredient's purchase/pricing unit."""
    if from_unit == to_unit:
        return float(quantity)
    return float(quantity) * unit_to_reference(from_unit, category) / unit_to_reference(to_unit, category)


def calculate_ingredient_cost(
    quantity: float,
    recipe_unit: str,
    purchase_unit: str,
    unit_price: float,
    category: str = "other",
) -> float:
    """Return consumption cost after converting recipe quantity to pricing unit."""
    purchase_quantity = convert_quantity(quantity, recipe_unit, purchase_unit, category)
    return round(purchase_quantity * float(unit_price), 2)
