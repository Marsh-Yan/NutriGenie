"""菜谱 Pydantic Schemas"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class RecipeIngredientItem(BaseModel):
    """菜谱中的食材项"""
    ingredient_id: int
    name: str
    quantity: float
    unit: str
    is_optional: bool = False


class RecipeStep(BaseModel):
    """菜谱步骤"""
    step: int
    content: str


class RecipeListItem(BaseModel):
    """菜谱列表项"""
    recipe_id: int
    name: str
    category: str
    cuisine_type: str
    difficulty: str
    prep_time: int
    cook_time: int
    image_url: Optional[str] = None
    total_calories: float
    tags: Optional[List[str]] = None

    class Config:
        from_attributes = True


class RecipeDetail(BaseModel):
    """菜谱详情"""
    recipe_id: int
    name: str
    description: Optional[str] = None
    category: str
    cuisine_type: str
    difficulty: str
    prep_time: int
    cook_time: int
    servings: int = 1
    steps: List[RecipeStep]
    image_url: Optional[str] = None
    ingredients: List[RecipeIngredientItem] = []
    nutrition: Optional[dict] = None
    estimated_cost: Optional[float] = None
    tags: Optional[List[str]] = None

    class Config:
        from_attributes = True


class RecipeListResponse(BaseModel):
    """菜谱列表响应"""
    total: int
    page: int
    page_size: int
    items: List[RecipeListItem]
