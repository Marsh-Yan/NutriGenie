"""Latest per-meal execution state; server owns the durable record."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, BigInteger, String, UniqueConstraint, func

from app.db.database import Base


class PlanExecutionEvent(Base):
    __tablename__ = "plan_execution_events"
    __table_args__ = (UniqueConstraint("plan_id", "day", "meal_slot", name="uq_plan_execution_slot"),)

    event_id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("meal_plans.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    day = Column(Integer, nullable=False)
    meal_slot = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="planned")
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
