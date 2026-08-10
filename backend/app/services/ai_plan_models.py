"""Structured models for AI-native meal plan generation.

The LLM owns the creative recipe output, while the application owns IDs and
derived totals.  Ingredient nutrition and cost values are estimates for the
exact line item quantity so that the backend can recompute recipe and plan
totals without requiring a recipe database row.
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
    nutrition_estimate: NutritionEstimate
    line_cost_estimate: float = Field(ge=0)
    optional: bool = False


class GeneratedRecipe(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="main_dish", min_length=1, max_length=40)
    cuisine_type: str = Field(default="家常", max_length=40)
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    prep_time_min: int = Field(default=0, ge=0, le=240)
    cook_time_min: int = Field(default=0, ge=0, le=360)
    servings: int = Field(default=1, ge=1, le=20)
    ingredients: List[GeneratedIngredient] = Field(min_length=1, max_length=40)
    steps: List[str] = Field(min_length=1, max_length=20)
    nutrition_estimate: NutritionEstimate
    cost_estimate: float = Field(ge=0)
    generation_note: str = Field(default="", max_length=500)

    @field_validator("steps")
    @classmethod
    def clean_steps(cls, value: List[str]) -> List[str]:
        steps = [item.strip() for item in value if item and item.strip()]
        if not steps:
            raise ValueError("菜谱步骤不能为空")
        return steps


class GeneratedMeal(BaseModel):
    day: int = Field(ge=1, le=7)
    slot: str = Field(min_length=1, max_length=30)
    recipe_index: int = Field(ge=0)
    servings: int = Field(default=1, ge=1, le=10)


class GeneratedPlan(BaseModel):
    """Raw plan returned by the LLM before backend normalization."""

    model_config = ConfigDict(extra="ignore")

    recipes: List[GeneratedRecipe] = Field(min_length=1, max_length=60)
    meals: List[GeneratedMeal] = Field(min_length=1, max_length=80)
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
