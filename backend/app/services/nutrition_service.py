"""营养计算服务

根据菜谱的食材清单及用量，累加计算营养数据（热量、蛋白质、脂肪、碳水、纤维）。

支持的单位转换:
  - 重量单位: g, kg, 斤, 两
  - 体积单位: ml, L, 勺, 汤匙, 茶匙
  - 计数单位: 个, 根, 颗, 瓣, 粒, 片, 块
"""

from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.services.recipe_service import get_recipe_ingredients

# ─── 单位 → 克 转换系数 ──────────────────────────

UNIT_TO_GRAM: Dict[str, float] = {
    # 标准重量单位
    "g": 1.0,
    "克": 1.0,
    "kg": 1000.0,
    "千克": 1000.0,
    "斤": 500.0,
    "两": 50.0,
    # 体积单位（近似为水密度）
    "ml": 1.0,
    "毫升": 1.0,
    "L": 1000.0,
    "升": 1000.0,
    "勺": 15.0,      # 1 中式汤匙 ≈ 15ml
    "汤匙": 15.0,
    "茶匙": 5.0,
    "小勺": 5.0,
    # 计数单位默认值（会按食材类型微调）
    "个": 50.0,
    "根": 100.0,
    "颗": 100.0,
    "瓣": 10.0,
    "粒": 5.0,
    "片": 20.0,
    "块": 50.0,
    "包": 200.0,
    "盒": 250.0,
    "把": 200.0,
    "撮": 2.0,
}

# ─── 按食材类型的单位重量调整 ────────────────────

CATEGORY_WEIGHT_ADJUST: Dict[str, Dict[str, float]] = {
    "vegetable": {"个": 150.0, "根": 80.0, "颗": 200.0, "把": 200.0},
    "fruit": {"个": 150.0, "颗": 20.0, "片": 30.0},
    "meat": {"块": 200.0, "片": 50.0, "个": 100.0},
    "seafood": {"个": 30.0, "条": 200.0, "只": 50.0},
    "egg": {"个": 50.0, "颗": 50.0},
    "dairy": {"盒": 250.0, "杯": 200.0, "片": 20.0},
    "condiment": {"勺": 15.0, "汤匙": 15.0, "茶匙": 5.0, "小勺": 5.0, "撮": 2.0, "粒": 1.0},
    "grain": {"碗": 200.0, "杯": 150.0, "个": 80.0},
}


def get_estimated_grams(quantity: float, unit: str, category: str = "other") -> float:
    """将食材用量估算为克数

    Args:
        quantity: 用量数值
        unit: 计量单位
        category: 食材分类

    Returns:
        估算的克数
    """
    # 先查按食材分类调整后的单位
    if category in CATEGORY_WEIGHT_ADJUST and unit in CATEGORY_WEIGHT_ADJUST[category]:
        return quantity * CATEGORY_WEIGHT_ADJUST[category][unit]

    # 再查通用单位表
    if unit in UNIT_TO_GRAM:
        return quantity * UNIT_TO_GRAM[unit]

    # 未知单位，按 1g 处理（调料类小分量一般影响不大）
    return quantity * 1.0


def calculate_recipe_nutrition(
    db: Session,
    recipe_id: int,
    servings: Optional[int] = None,
) -> dict:
    """根据食材清单计算一道菜的营养数据

    Args:
        db: 数据库会话
        recipe_id: 菜谱 ID
        servings: 按指定份数计算，默认使用 recipe.servings

    Returns:
        {
            "calories": float,
            "protein": float,
            "fat": float,
            "carbs": float,
            "fiber": float,
            "ingredient_details": [...],
        }
    """
    from app.models.recipe import Recipe

    recipe = db.query(Recipe).filter(Recipe.recipe_id == recipe_id).first()
    if not recipe:
        raise ValueError(f"Recipe {recipe_id} not found")

    target_servings = servings or recipe.servings or 1
    ingredients = get_recipe_ingredients(db, recipe_id)

    total = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0, "fiber": 0.0}
    details = []

    for ing in ingredients:
        nut = ing.get("nutrition")
        if not nut:
            continue

        # 估算克数
        grams = get_estimated_grams(
            quantity=ing["quantity"],
            unit=ing["unit"],
            category=ing.get("category", "other"),
        )

        # 营养 = (克数 / 100) × 每100g营养
        factor = grams / 100.0
        item_nutrition = {
            "calories": round(nut["calories"] * factor, 1),
            "protein": round(nut["protein"] * factor, 1),
            "fat": round(nut["fat"] * factor, 1),
            "carbs": round(nut["carbs"] * factor, 1),
            "fiber": round(nut["fiber"] * factor, 1),
        }

        for key in total:
            total[key] += item_nutrition[key]

        details.append({
            "ingredient_id": ing["ingredient_id"],
            "name": ing["name"],
            "quantity": ing["quantity"],
            "unit": ing["unit"],
            "estimated_grams": round(grams, 1),
            "nutrition": item_nutrition,
        })

    # 按份数折算每份营养
    per_serving = {
        k: round(v / target_servings, 1) for k, v in total.items()
    }

    return {
        "recipe_id": recipe_id,
        "name": recipe.name,
        "servings": target_servings,
        "total": {k: round(v, 1) for k, v in total.items()},
        "per_serving": per_serving,
        "ingredient_details": details,
    }


def calculate_nutrition_for_meals(
    db: Session,
    meal_plan: List[Tuple[int, int]],  # [(recipe_id, servings), ...]
) -> dict:
    """计算多道菜的营养总和（用于周计划的每日汇总）

    Args:
        db: 数据库会话
        meal_plan: [(recipe_id, servings), ...] 每餐菜谱和份数

    Returns:
        汇总营养数据
    """
    total = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0, "fiber": 0.0}
    details = []

    for recipe_id, servings in meal_plan:
        result = calculate_recipe_nutrition(db, recipe_id, servings=servings)
        per_serving = result["per_serving"]
        for key in total:
            total[key] += per_serving[key] * servings
        details.append({
            "recipe_id": recipe_id,
            "name": result["name"],
            "servings": servings,
            "nutrition": per_serving,
        })

    return {
        "total": {k: round(v, 1) for k, v in total.items()},
        "meals": details,
    }
