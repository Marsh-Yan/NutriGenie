"""Generation run state for initial plans and conversational edits."""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON, func

from app.db.database import Base


class MealPlanRun(Base):
    __tablename__ = "meal_plan_runs"

    run_id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("meal_plans.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    base_version_id = Column(Integer, nullable=True, index=True)
    trigger_message_id = Column(Integer, nullable=True, index=True)
    client_request_id = Column(String(100), nullable=True, index=True)
    status = Column(
        Enum("pending", "running", "completed", "failed"),
        default="pending",
        nullable=False,
    )
    current_node = Column(String(80), nullable=True)
    repair_attempts = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    output_version_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
