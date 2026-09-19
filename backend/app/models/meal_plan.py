"""饮食规划结果模型"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    JSON,
    DateTime,
    DECIMAL,
    Enum,
    ForeignKey,
    func,
)

from app.db.database import Base


class MealPlan(Base):
    __tablename__ = "meal_plans"

    plan_id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(
        Integer,
        ForeignKey("profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(
        Enum("pending", "running", "completed", "failed"),
        default="pending",
    )
    user_input = Column(Text, nullable=False)
    duration_days = Column(Integer, default=7)
    total_budget = Column(DECIMAL(8, 2), default=0)
    title = Column(String(100), nullable=True)
    source_plan_id = Column(Integer, ForeignKey("meal_plans.plan_id", ondelete="SET NULL"), nullable=True)
    archived_at = Column(DateTime, nullable=True)
    result_json = Column(JSON, default=None, comment="完整规划结果快照")
    current_version_id = Column(Integer, nullable=True, index=True)
    current_node = Column(String(50), default=None, comment="当前执行节点")
    error_message = Column(Text, default=None)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, default=None)
