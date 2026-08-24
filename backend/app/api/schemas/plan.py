"""API schemas for AI-native meal plans and conversational edits."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class PlanCreate(BaseModel):
    profile_id: int
    user_input: str = Field(..., min_length=1, max_length=1000)
    duration_days: int = Field(default=7, ge=1, le=7)
    total_budget: float = Field(default=0, ge=0)


class PlanCreateResponse(BaseModel):
    plan_id: int
    status: str
    created_at: datetime
    links: dict


class PlanListItem(BaseModel):
    """当前用户可访问的历史规划摘要"""
    plan_id: int
    status: str
    user_input: str
    duration_days: int
    total_budget: float
    created_at: datetime
    completed_at: Optional[datetime] = None


class StepInfo(BaseModel):
    name: str
    status: str
    order: int


class ProgressInfo(BaseModel):
    total_steps: int = 7
    completed_steps: int = 0
    current_step: int = 1
    step_name: str = ""
    steps: List[StepInfo] = Field(default_factory=list)


class PlanStatusResponse(BaseModel):
    plan_id: int
    status: str
    run_id: Optional[int] = None
    run_status: Optional[str] = None
    current_node: Optional[str] = None
    current_version_id: Optional[int] = None
    has_current_version: bool = False
    progress: Optional[ProgressInfo] = None
    error: Optional[str] = None
    last_error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class PlanRunningResponse(BaseModel):
    plan_id: int
    status: str = "running"
    message: str = "规划正在生成中，请稍后查看。"
    current_node: Optional[str] = None
    current_version_id: Optional[int] = None
    has_current_version: bool = False


class GeneratedNutrition(BaseModel):
    calories: float = 0
    protein_g: float = 0
    fat_g: float = 0
    carbs_g: float = 0
    fiber_g: float = 0


class GeneratedIngredientItem(BaseModel):
    name: str
    quantity: float
    unit: str
    optional: bool = False
    nutrition_estimate: GeneratedNutrition
    line_cost_estimate: float = 0


class GeneratedRecipeItem(BaseModel):
    recipe_key: str
    source: str = "llm_generated"
    name: str
    category: str
    cuisine_type: str = "家常"
    difficulty: str = "easy"
    prep_time_min: int = 0
    cook_time_min: int = 0
    servings: int = 1
    ingredients: List[GeneratedIngredientItem] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    nutrition: GeneratedNutrition
    nutrition_estimate: Optional[GeneratedNutrition] = None
    declared_nutrition: Optional[GeneratedNutrition] = None
    estimated_cost: float = 0
    cost_estimate: Optional[float] = None
    declared_cost: Optional[float] = None
    estimate_source: str = "llm_estimate"
    generation_note: str = ""


class GeneratedMealItem(BaseModel):
    recipe_key: str
    name: str
    serving_size: int = 1
    nutrition: GeneratedNutrition


class WeeklyPlanItem(BaseModel):
    day: int
    meals: Dict[str, GeneratedMealItem] = Field(default_factory=dict)
    total_nutrition: GeneratedNutrition


class NutritionReport(BaseModel):
    avg_daily_calories: float = 0
    total_calories: float = 0
    protein_g: float = 0
    fat_g: float = 0
    carbs_g: float = 0
    fiber_g: float = 0
    protein_pct: float = 0
    fat_pct: float = 0
    carbs_pct: float = 0
    recommendation: str = ""


class ShoppingItem(BaseModel):
    ingredient_id: int = 0
    name: str
    quantity: float
    unit: str
    estimated_cost: float
    for_recipes: List[dict] = Field(default_factory=list)


class ShoppingList(BaseModel):
    total_cost: float = 0
    items: List[ShoppingItem] = Field(default_factory=list)
    by_category: dict = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    code: str
    message: str
    severity: Literal["error", "warning"]
    path: Optional[str] = None


class PlanValidation(BaseModel):
    status: str = "passed"
    passed: bool = True
    issues: List[ValidationIssue] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    derived: dict = Field(default_factory=dict)


class GenerationMeta(BaseModel):
    strategy: str = "ai_native_v1"
    rag_enabled: bool = False
    rag_used: bool = False
    rag_sources: List[dict] = Field(default_factory=list)
    rag_error: Optional[str] = None
    repair_attempts: int = 0
    estimate_source: str = "llm_estimate"
    intent_snapshot: dict = Field(default_factory=dict)
    constraints_snapshot: dict = Field(default_factory=dict)


class PlanResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str = "ai_native_v1"
    version_id: Optional[int] = None
    version_no: Optional[int] = None
    recipes: List[GeneratedRecipeItem] = Field(default_factory=list)
    weekly_plan: List[WeeklyPlanItem] = Field(default_factory=list)
    nutrition_report: NutritionReport
    shopping_list: ShoppingList
    validation: PlanValidation = Field(default_factory=PlanValidation)
    generation_meta: GenerationMeta = Field(default_factory=GenerationMeta)
    summary: str = ""


class PlanResultResponse(BaseModel):
    plan_id: int
    status: str
    profile_id: int
    user_input: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[PlanResult] = None


class PlanMessageCreate(BaseModel):
    message: str = Field(default="", max_length=1000)
    action: Optional[dict] = None
    client_request_id: Optional[str] = Field(default=None, max_length=100)


class PlanMessageResponse(BaseModel):
    message_id: int
    plan_id: int
    version_id: Optional[int] = None
    role: str
    content: str
    action: Optional[dict] = None
    status: str
    created_at: datetime


class PlanRunResponse(BaseModel):
    run_id: int
    plan_id: int
    status: str
    current_node: Optional[str] = None
    base_version_id: Optional[int] = None
    output_version_id: Optional[int] = None
    error: Optional[str] = None
