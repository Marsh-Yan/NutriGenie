"""数据库连接与会话管理"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有表"""
    from app.models import (  # noqa: F401 - 确保模型被注册
        profile,
        recipe,
        ingredient,
        recipe_ingredient,
        ingredient_nutrition,
        meal_plan,
        meal_plan_version,
        meal_plan_message,
        meal_plan_run,
        user,
        knowledge,
    )
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "profiles" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("profiles")}
        if "user_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE profiles ADD COLUMN user_id INTEGER NULL"))
