"""Store explicit user feedback without modifying recommendation weights."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.v21 import FeedbackCreate
from app.db.database import get_db
from app.models.meal_plan import MealPlan
from app.models.profile import Profile
from app.models.recipe import Recipe
from app.models.user import User
from app.models.user_feedback import UserFeedback
from app.services.security import get_current_user

router = APIRouter(tags=["feedback"])


@router.post("/feedback", status_code=201)
def api_create_feedback(
    data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.plan_id is not None:
        plan = db.get(MealPlan, data.plan_id)
        profile = db.get(Profile, plan.profile_id) if plan else None
        if not profile or (current_user.role != "admin" and profile.user_id != current_user.user_id):
            raise HTTPException(status_code=404, detail="规划任务不存在")
    if data.recipe_id is not None and not db.get(Recipe, data.recipe_id):
        raise HTTPException(status_code=404, detail="菜谱不存在")
    if data.plan_id is None and data.recipe_id is None:
        raise HTTPException(status_code=422, detail="请指定计划或菜谱")
    feedback = UserFeedback(user_id=current_user.user_id, **data.model_dump())
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return {"feedback_id": feedback.feedback_id, "created_at": feedback.created_at}
