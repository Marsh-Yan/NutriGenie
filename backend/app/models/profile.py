"""用户画像模型"""

from sqlalchemy import Column, Integer, String, DECIMAL, JSON, DateTime, func, Enum, ForeignKey

from app.db.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    profile_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True, index=True)
    age = Column(Integer, nullable=False)
    gender = Column(Enum("male", "female"), nullable=False)
    height = Column(DECIMAL(5, 1), nullable=False, comment="cm")
    weight = Column(DECIMAL(5, 1), nullable=False, comment="kg")
    diet_type = Column(
        String(50),
        nullable=False,
        default="balanced",
        comment="balanced|keto|high_protein|gluten_free|vegan|healthy",
    )
    health_goal = Column(
        String(50),
        nullable=False,
        default="healthy",
        comment="fat_loss|muscle_gain|blood_sugar|healthy",
    )
    allergies = Column(JSON, default=None, comment='["花生","海鲜"]')
    daily_budget = Column(DECIMAL(8, 2), default=0, comment="元")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
