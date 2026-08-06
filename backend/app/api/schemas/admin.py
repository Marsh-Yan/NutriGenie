"""Request models used only by the administrator console."""

from typing import Optional

from pydantic import BaseModel, Field


class NutritionWrite(BaseModel):
    calories: float = Field(default=0, ge=0)
    protein: float = Field(default=0, ge=0)
    fat: float = Field(default=0, ge=0)
    carbs: float = Field(default=0, ge=0)
    fiber: float = Field(default=0, ge=0)


class IngredientWrite(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=50)
    unit: str = Field(default="g", min_length=1, max_length=20)
    unit_price: float = Field(default=0, ge=0)
    season_tags: Optional[list[str]] = None
    storage_days: int = Field(default=7, ge=0, le=365)
    nutrition: NutritionWrite = Field(default_factory=NutritionWrite)


class RecipeIngredientWrite(BaseModel):
    ingredient_id: int = Field(gt=0)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=20)
    is_optional: bool = False


class RecipeWrite(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    category: str = Field(min_length=1, max_length=50)
    cuisine_type: str = Field(min_length=1, max_length=20)
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")
    prep_time: int = Field(default=0, ge=0)
    cook_time: int = Field(default=0, ge=0)
    servings: int = Field(default=1, ge=1, le=20)
    steps: list[dict] = Field(default_factory=list)
    image_url: Optional[str] = Field(default=None, max_length=255)
    nutrition: NutritionWrite = Field(default_factory=NutritionWrite)
    tags: Optional[list[str]] = None
    ingredients: list[RecipeIngredientWrite] = Field(default_factory=list)


class KnowledgeDocumentWrite(BaseModel):
    recipe_id: int = Field(gt=0)
    content: str = Field(min_length=20, max_length=50000)
