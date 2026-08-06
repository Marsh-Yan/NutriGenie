"""食材相关数据查询服务"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import cast, Text

from app.models.ingredient import Ingredient
from app.models.ingredient_nutrition import IngredientNutrition


def get_ingredient(db: Session, ingredient_id: int) -> Optional[Ingredient]:
    return db.query(Ingredient).filter(Ingredient.ingredient_id == ingredient_id).first()


def get_ingredients(
    db: Session,
    category: Optional[str] = None,
    season: Optional[str] = None,
) -> Tuple[List[dict], int]:
    """获取食材列表，支持分类和季节筛选"""
    query = db.query(Ingredient)

    if category:
        query = query.filter(Ingredient.category == category)
    if season:
        query = query.filter(cast(Ingredient.season_tags, Text).contains(season))

    total = query.count()
    items = query.all()

    result = []
    for ing in items:
        nut = (
            db.query(IngredientNutrition)
            .filter(IngredientNutrition.ingredient_id == ing.ingredient_id)
            .first()
        )
        result.append(
            {
                "ingredient_id": ing.ingredient_id,
                "name": ing.name,
                "category": ing.category,
                "unit": ing.unit,
                "unit_price": float(ing.unit_price),
                "season_tags": ing.season_tags,
                "nutrition_per_100g": {
                    "calories": float(nut.calories_per_100g) if nut else 0,
                    "protein": float(nut.protein_per_100g) if nut else 0,
                    "fat": float(nut.fat_per_100g) if nut else 0,
                    "carbs": float(nut.carbs_per_100g) if nut else 0,
                    "fiber": float(nut.fiber_per_100g) if nut else 0,
                }
                if nut
                else None,
            }
        )

    return result, total


def get_all_ingredients(db: Session) -> List[Ingredient]:
    """获取所有食材（用于推荐引擎）"""
    return db.query(Ingredient).all()
