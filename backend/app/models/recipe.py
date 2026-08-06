"""菜谱模型"""

from sqlalchemy import Column, Integer, String, Text, DECIMAL, JSON, Enum, DateTime, func

from app.db.database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    recipe_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    category = Column(
        String(50),
        nullable=False,
        comment="main_dish|side_dish|soup|staple|light_meal",
    )
    cuisine_type = Column(String(20), nullable=False, comment="chinese|western")
    difficulty = Column(Enum("easy", "medium", "hard"), default="medium")
    prep_time = Column(Integer, nullable=False, comment="准备时间，分钟")
    cook_time = Column(Integer, nullable=False, comment="烹饪时间，分钟")
    servings = Column(Integer, default=1, comment="份数")
    steps = Column(JSON, nullable=False, comment='[{"step":1,"content":"步骤描述"}]')
    image_url = Column(String(255), default=None)
    total_calories = Column(DECIMAL(7, 1), default=0, comment="每份热量，kcal")
    total_protein = Column(DECIMAL(7, 1), default=0, comment="每份蛋白质，g")
    total_fat = Column(DECIMAL(7, 1), default=0, comment="每份脂肪，g")
    total_carbs = Column(DECIMAL(7, 1), default=0, comment="每份碳水，g")
    total_fiber = Column(DECIMAL(7, 1), default=0, comment="每份膳食纤维，g")
    tags = Column(JSON, default=None, comment='["高蛋白","快手菜"]')
    created_at = Column(DateTime, server_default=func.now())
