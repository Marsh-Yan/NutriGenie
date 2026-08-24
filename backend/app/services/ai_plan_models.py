"""Structured models for AI-native meal plan generation.

The LLM owns creative recipe output. Ingredient nutrition and price fields are
optional provider declarations retained only for audit; V2 replaces them with
facts calculated from the trusted ingredient catalog before validation.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NutritionEstimate(BaseModel):
    calories: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fiber_g: float = Field(default=0, ge=0)


class GeneratedIngredient(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=20)
    optional: bool = False
    # V1 providers may still return declared estimates. V2 never trusts them:
    # the normalizer overwrites these values from the ingredient catalog.
    nutrition_estimate: Optional[NutritionEstimate] = None
    line_cost_estimate: Optional[float] = Field(default=None, ge=0)
    declared_nutrition_estimate: Optional[NutritionEstimate] = None
    declared_line_cost_estimate: Optional[float] = Field(default=None, ge=0)
    input_name: Optional[str] = None
    ingredient_id: Optional[int] = None
    catalog_name: Optional[str] = None
    estimated_grams: Optional[float] = Field(default=None, ge=0)
    resolution_source: Optional[Literal["exact", "alias", "normalized"]] = None
    data_source: Optional[str] = None


class GeneratedRecipe(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="main_dish", min_length=1, max_length=40)
    cuisine_type: str = Field(default="家常", max_length=40)
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    prep_time_min: int = Field(default=0, ge=0, le=240)
    cook_time_min: int = Field(default=0, ge=0, le=360)
    servings: int = Field(default=1, ge=1, le=20)
    meal_slots: List[Literal["breakfast", "lunch", "dinner", "snack"]] = Field(default_factory=list)
    ingredients: List[GeneratedIngredient] = Field(min_length=1, max_length=40)
    steps: List[str] = Field(min_length=1, max_length=20)
    nutrition_estimate: Optional[NutritionEstimate] = None
    cost_estimate: Optional[float] = Field(default=None, ge=0)
    declared_nutrition_estimate: Optional[NutritionEstimate] = None
    declared_cost_estimate: Optional[float] = Field(default=None, ge=0)
    generation_note: str = Field(default="", max_length=500)

    @field_validator("steps")
    @classmethod
    def clean_steps(cls, value: List[str]) -> List[str]:
        steps = [item.strip() for item in value if item and item.strip()]
        if not steps:
            raise ValueError("菜谱步骤不能为空")
        return steps

    @field_validator("meal_slots")
    @classmethod
    def unique_meal_slots(cls, value: List[str]) -> List[str]:
        return list(dict.fromkeys(value))


class GeneratedMeal(BaseModel):
    day: int = Field(ge=1, le=7)
    slot: str = Field(min_length=1, max_length=30)
    recipe_index: int = Field(ge=0)
    servings: int = Field(default=1, ge=1, le=10)


class GeneratedPlan(BaseModel):
    """Raw plan returned by the LLM before backend normalization."""

    model_config = ConfigDict(extra="ignore")

    recipes: List[GeneratedRecipe] = Field(min_length=1, max_length=60)
    meals: List[GeneratedMeal] = Field(default_factory=list, max_length=80)
    summary: str = Field(default="", max_length=2000)


class ValidationIssue(BaseModel):
    code: str
    message: str
    severity: Literal["error", "warning"]
    path: Optional[str] = None


class PlanValidationResult(BaseModel):
    status: Literal["passed", "warning", "failed"]
    passed: bool
    issues: List[ValidationIssue] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    derived: dict = Field(default_factory=dict)
