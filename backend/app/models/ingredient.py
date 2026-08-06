"""食材模型"""

from sqlalchemy import Column, Integer, String, DECIMAL, JSON, DateTime, func

from app.db.database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    ingredient_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    category = Column(
        String(50),
        nullable=False,
        comment="vegetable|meat|seafood|dairy|grain|fruit|condiment|egg|other",
    )
    unit = Column(String(20), nullable=False, default="g", comment="计量单位")
    unit_price = Column(DECIMAL(8, 2), default=0, comment="每单位价格（元）")
    season_tags = Column(
        JSON, default=None, comment='["春季","夏季"] 或 null(全年)'
    )
    storage_days = Column(Integer, default=7, comment="建议存放天数")
    created_at = Column(DateTime, server_default=func.now())
