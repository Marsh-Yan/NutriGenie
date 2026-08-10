"""Conversation messages associated with a meal plan."""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func

from app.db.database import Base


class MealPlanMessage(Base):
    __tablename__ = "meal_plan_messages"

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("meal_plans.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("meal_plan_versions.version_id", ondelete="SET NULL"), nullable=True, index=True)
    role = Column(String(20), nullable=False, default="user")
    content = Column(Text, nullable=False)
    action_json = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="accepted")
    created_at = Column(DateTime, server_default=func.now())
