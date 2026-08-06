"""食材营养数据模型"""

from sqlalchemy import Column, Integer, DECIMAL, ForeignKey

from app.db.database import Base


class IngredientNutrition(Base):
    __tablename__ = "ingredient_nutrition"

    nutrition_id = Column(Integer, primary_key=True, autoincrement=True)
    ingredient_id = Column(
        Integer,
        ForeignKey("ingredients.ingredient_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    calories_per_100g = Column(DECIMAL(7, 1), default=0, comment="kcal")
    protein_per_100g = Column(DECIMAL(7, 1), default=0, comment="g")
    fat_per_100g = Column(DECIMAL(7, 1), default=0, comment="g")
    carbs_per_100g = Column(DECIMAL(7, 1), default=0, comment="g")
    fiber_per_100g = Column(DECIMAL(7, 1), default=0, comment="g")
