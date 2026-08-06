"""菜谱-食材关联模型"""

from sqlalchemy import Column, Integer, DECIMAL, String, ForeignKey, SmallInteger

from app.db.database import Base


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    recipe_id = Column(
        Integer, ForeignKey("recipes.recipe_id", ondelete="CASCADE"), primary_key=True
    )
    ingredient_id = Column(
        Integer,
        ForeignKey("ingredients.ingredient_id", ondelete="CASCADE"),
        primary_key=True,
    )
    quantity = Column(DECIMAL(8, 2), nullable=False, comment="用量数值")
    unit = Column(String(20), nullable=False, comment="g|ml|个|根|把|勺")
    is_optional = Column(SmallInteger, default=0, comment="是否可选替代")
