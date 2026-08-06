"""食材 Pydantic Schemas"""

from typing import List, Optional
from pydantic import BaseModel


class NutritionPer100g(BaseModel):
    """每 100g 营养数据"""
    calories: float = 0
    protein: float = 0
    fat: float = 0
    carbs: float = 0
    fiber: float = 0


class IngredientItem(BaseModel):
    """食材项"""
    ingredient_id: int
    name: str
    category: str
    unit: str
    unit_price: float
    season_tags: Optional[List[str]] = None
    nutrition_per_100g: Optional[NutritionPer100g] = None


class IngredientListResponse(BaseModel):
    """食材列表响应"""
    total: int
    items: List[IngredientItem]
