"""Explicit feedback, stored without changing safety or ranking rules."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.database import Base


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    feedback_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("meal_plans.plan_id", ondelete="SET NULL"), nullable=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.recipe_id", ondelete="SET NULL"), nullable=True, index=True)
    feedback_type = Column(String(30), nullable=False)
    rating = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
