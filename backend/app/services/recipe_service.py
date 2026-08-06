"""菜谱相关数据查询服务"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import cast, Text

from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.models.ingredient import Ingredient
from app.models.ingredient_nutrition import IngredientNutrition
from app.services.cost_service import calculate_ingredient_cost


def get_recipe(db: Session, recipe_id: int) -> Optional[Recipe]:
    return db.query(Recipe).filter(Recipe.recipe_id == recipe_id).first()


def get_recipes(
    db: Session,
    category: Optional[str] = None,
    cuisine_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    tags: Optional[List[str]] = None,
    max_prep_time: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Recipe], int]:
    """获取菜谱列表，支持筛选和分页，返回 (items, total)"""
    query = db.query(Recipe)

    if category:
        query = query.filter(Recipe.category == category)
    if cuisine_type:
        query = query.filter(Recipe.cuisine_type == cuisine_type)
    if difficulty:
        query = query.filter(Recipe.difficulty == difficulty)
    if max_prep_time:
        query = query.filter(Recipe.prep_time + Recipe.cook_time <= max_prep_time)
    if tags:
        for tag in tags:
            query = query.filter(cast(Recipe.tags, Text).contains(tag))

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_all_recipes(db: Session) -> List[Recipe]:
    """获取所有菜谱（用于推荐引擎候选池）"""
    return db.query(Recipe).all()


def get_recipe_ingredients(db: Session, recipe_id: int) -> List[dict]:
    """获取菜谱的食材清单（含食材详情和营养数据）"""
    results = (
        db.query(RecipeIngredient, Ingredient, IngredientNutrition)
        .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.ingredient_id)
        .join(
            IngredientNutrition,
            RecipeIngredient.ingredient_id == IngredientNutrition.ingredient_id,
            isouter=True,
        )
        .filter(RecipeIngredient.recipe_id == recipe_id)
        .all()
    )

    return [
        {
            "ingredient_id": ri.ingredient_id,
            "name": ing.name,
            "category": ing.category,
            "quantity": float(ri.quantity),
            "unit": ri.unit,
            "purchase_unit": ing.unit,
            "is_optional": bool(ri.is_optional),
            "unit_price": float(ing.unit_price),
            "estimated_cost": calculate_ingredient_cost(
                quantity=float(ri.quantity),
                recipe_unit=ri.unit,
                purchase_unit=ing.unit,
                unit_price=float(ing.unit_price),
                category=ing.category,
            ),
            "nutrition": {
                "calories": float(nut.calories_per_100g) if nut else 0,
                "protein": float(nut.protein_per_100g) if nut else 0,
                "fat": float(nut.fat_per_100g) if nut else 0,
                "carbs": float(nut.carbs_per_100g) if nut else 0,
                "fiber": float(nut.fiber_per_100g) if nut else 0,
            }
            if nut
            else None,
        }
        for ri, ing, nut in results
    ]
