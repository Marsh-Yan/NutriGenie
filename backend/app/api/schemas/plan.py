"""饮食规划 Pydantic Schemas"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ─── 创建规划 ─────────────────────────────────────

class PlanCreate(BaseModel):
    """创建饮食规划请求"""
    profile_id: int
    user_input: str = Field(..., min_length=1, max_length=1000)
    duration_days: int = Field(default=7, ge=1, le=30)
    total_budget: float = Field(default=0, ge=0)


class PlanCreateResponse(BaseModel):
    """创建饮食规划响应 (202 Accepted)"""
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


# ─── 规划状态 ─────────────────────────────────────

class StepInfo(BaseModel):
    """步骤信息"""
    name: str
    status: str  # completed / running / pending
    order: int


class ProgressInfo(BaseModel):
    """进度信息"""
    total_steps: int = 6
    completed_steps: int = 0
    current_step: int = 1
    step_name: str = ""
    steps: List[StepInfo] = Field(default_factory=list)


class PlanStatusResponse(BaseModel):
    """规划状态响应"""
    plan_id: int
    status: str  # pending / running / completed / failed
    current_node: Optional[str] = None
    progress: Optional[ProgressInfo] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


# ─── 规划结果 ─────────────────────────────────────

class RecipeScore(BaseModel):
    """菜谱评分"""
    health: float = 0
    budget: float = 0
    preference: float = 0
    season: float = 0
    variety: float = 0
    utilization: float = 0


class RecipeNutrition(BaseModel):
    """菜谱营养"""
    calories: float = 0
    protein: float = 0
    fat: float = 0
    carbs: float = 0
    fiber: float = 0


class Top5Item(BaseModel):
    """TOP5 推荐项"""
    recipe_id: int
    name: str
    image_url: Optional[str] = None
    category: str
    cuisine_type: str
    difficulty: str
    prep_time: int
    cook_time: int
    scores: RecipeScore
    total_score: float
    nutrition: RecipeNutrition
    estimated_cost: float
    explanation: str


class MealNutrition(BaseModel):
    """每餐营养"""
    calories: float = 0
    protein: float = 0
    fat: float = 0
    carbs: float = 0


class Meal(BaseModel):
    """一餐"""
    recipe_id: int
    name: str
    serving_size: int = 1
    nutrition: MealNutrition


class DayMeals(BaseModel):
    """一天的餐食"""
    breakfast: Optional[Meal] = None
    lunch: Optional[Meal] = None
    dinner: Optional[Meal] = None


class WeeklyPlanItem(BaseModel):
    """一周规划中的一天"""
    day: int
    meals: DayMeals
    total_nutrition: MealNutrition


class NutritionReport(BaseModel):
    """营养报告"""
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
    """采购项"""
    ingredient_id: int
    name: str
    quantity: float
    unit: str
    estimated_cost: float
    for_recipes: List[dict] = []


class ShoppingList(BaseModel):
    """采购清单"""
    total_cost: float = 0
    items: List[ShoppingItem] = []
    by_category: dict = {}


class PlanResult(BaseModel):
    """规划完整结果"""
    top5: List[Top5Item]
    weekly_plan: List[WeeklyPlanItem]
    nutrition_report: NutritionReport
    shopping_list: ShoppingList
    summary: str = ""


class PlanResultResponse(BaseModel):
    """规划结果响应"""
    plan_id: int
    status: str
    profile_id: int
    user_input: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[PlanResult] = None


# ─── 简单结果（运行中） ──────────────────────────

class PlanRunningResponse(BaseModel):
    """规划运行中响应"""
    plan_id: int
    status: str = "running"
    message: str = "规划正在生成中，请稍后查看。"
    current_node: Optional[str] = None
