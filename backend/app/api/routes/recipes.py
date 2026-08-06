"""菜谱 API 路由"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.schemas.recipe import (
    RecipeListItem, RecipeDetail, RecipeListResponse,
    RecipeIngredientItem, RecipeStep,
)
from app.services.recipe_service import (
    get_recipe, get_recipes, get_recipe_ingredients,
)

router = APIRouter(tags=["recipes"])


@router.get("/recipes", response_model=RecipeListResponse)
def api_get_recipes(
    category: Optional[str] = None,
    cuisine_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    max_prep_time: Optional[int] = None,
    tags: Optional[str] = Query(None, description="逗号分隔的标签"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    tag_list = tags.split(",") if tags else None
    items, total = get_recipes(
        db,
        category=category,
        cuisine_type=cuisine_type,
        difficulty=difficulty,
        max_prep_time=max_prep_time,
        tags=tag_list,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            RecipeListItem(
                recipe_id=r.recipe_id,
                name=r.name,
                category=r.category,
                cuisine_type=r.cuisine_type,
                difficulty=r.difficulty,
                prep_time=r.prep_time,
                cook_time=r.cook_time,
                image_url=r.image_url,
                total_calories=float(r.total_calories),
                tags=r.tags,
            )
            for r in items
        ],
    }


@router.get("/recipes/{recipe_id}", response_model=RecipeDetail)
def api_get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="菜谱不存在")

    ingredients_raw = get_recipe_ingredients(db, recipe_id)
    total_cost = sum(i["estimated_cost"] for i in ingredients_raw)

    ingredients = [
        RecipeIngredientItem(
            ingredient_id=i["ingredient_id"],
            name=i["name"],
            quantity=i["quantity"],
            unit=i["unit"],
            is_optional=i["is_optional"],
        )
        for i in ingredients_raw
    ]

    # 从食材营养汇总计算菜谱营养
    nutrition = {
        "calories": float(recipe.total_calories),
        "protein": float(recipe.total_protein),
        "fat": float(recipe.total_fat),
        "carbs": float(recipe.total_carbs),
        "fiber": float(recipe.total_fiber),
    }

    return RecipeDetail(
        recipe_id=recipe.recipe_id,
        name=recipe.name,
        description=recipe.description,
        category=recipe.category,
        cuisine_type=recipe.cuisine_type,
        difficulty=recipe.difficulty,
        prep_time=recipe.prep_time,
        cook_time=recipe.cook_time,
        servings=recipe.servings,
        steps=[RecipeStep(**s) for s in (recipe.steps or [])],
        image_url=recipe.image_url,
        ingredients=ingredients,
        nutrition=nutrition,
        estimated_cost=round(total_cost, 2),
        tags=recipe.tags,
    )


@router.get("/recipes/{recipe_id}/nutrition")
def api_get_recipe_nutrition(recipe_id: int, db: Session = Depends(get_db)):
    recipe = get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="菜谱不存在")

    ingredients_raw = get_recipe_ingredients(db, recipe_id)
    total_cost = sum(i["estimated_cost"] for i in ingredients_raw)

    return {
        "recipe_id": recipe_id,
        "name": recipe.name,
        "nutrition": {
            "calories": float(recipe.total_calories),
            "protein": float(recipe.total_protein),
            "fat": float(recipe.total_fat),
            "carbs": float(recipe.total_carbs),
            "fiber": float(recipe.total_fiber),
        },
        "ingredients": [
            {
                "name": i["name"],
                "quantity": i["quantity"],
                "unit": i["unit"],
                "estimated_cost": i["estimated_cost"],
                "nutrition_per_100g": i["nutrition"],
            }
            for i in ingredients_raw
        ],
        "total_estimated_cost": round(total_cost, 2),
    }
