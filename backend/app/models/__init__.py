"""模型注册 - 确保所有模型被 SQLAlchemy Base 发现"""
from app.models.profile import Profile
from app.models.recipe import Recipe
from app.models.ingredient import Ingredient
from app.models.recipe_ingredient import RecipeIngredient
from app.models.ingredient_nutrition import IngredientNutrition
from app.models.meal_plan import MealPlan
from app.models.meal_plan_version import MealPlanVersion
from app.models.meal_plan_message import MealPlanMessage
from app.models.meal_plan_run import MealPlanRun
from app.models.plan_execution_event import PlanExecutionEvent
from app.models.user_feedback import UserFeedback
from app.models.pantry_item import PantryItem
from app.models.user import User
from app.models.knowledge import KnowledgeDocumentRecord, KnowledgeChunkRecord, KnowledgeIngestionJob

__all__ = [
    "Profile",
    "Recipe",
    "Ingredient",
    "RecipeIngredient",
    "IngredientNutrition",
    "MealPlan",
    "MealPlanVersion",
    "MealPlanMessage",
    "MealPlanRun",
    "PlanExecutionEvent",
    "UserFeedback",
    "PantryItem",
    "User",
    "KnowledgeDocumentRecord",
    "KnowledgeChunkRecord",
    "KnowledgeIngestionJob",
]
