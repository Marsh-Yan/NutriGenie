"""Immutable AI-native meal plan versions."""

from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Text, func

from app.db.database import Base


class MealPlanVersion(Base):
    __tablename__ = "meal_plan_versions"

    version_id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("meal_plans.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False)
    parent_version_id = Column(Integer, nullable=True, index=True)
    trigger_message_id = Column(Integer, nullable=True, index=True)
    result_json = Column(JSON, nullable=False)
    validation_json = Column(JSON, nullable=True)
    model_name = Column(String(120), nullable=True)
    prompt_version = Column(String(80), nullable=True)
    rag_meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
