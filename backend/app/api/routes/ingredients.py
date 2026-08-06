"""食材 API 路由"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.schemas.ingredient import IngredientItem, IngredientListResponse, NutritionPer100g
from app.services.ingredient_service import get_ingredients

router = APIRouter(tags=["ingredients"])


@router.get("/ingredients", response_model=IngredientListResponse)
def api_get_ingredients(
    category: Optional[str] = None,
    season: Optional[str] = Query(None, description="春/夏/秋/冬"),
    db: Session = Depends(get_db),
):
    items, total = get_ingredients(db, category=category, season=season)
    return {
        "total": total,
        "items": [
            IngredientItem(
                ingredient_id=i["ingredient_id"],
                name=i["name"],
                category=i["category"],
                unit=i["unit"],
                unit_price=i["unit_price"],
                season_tags=i["season_tags"],
                nutrition_per_100g=NutritionPer100g(**i["nutrition_per_100g"])
                if i.get("nutrition_per_100g")
                else None,
            )
            for i in items
        ],
    }
