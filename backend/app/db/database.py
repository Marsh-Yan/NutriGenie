"""数据库连接与会话管理"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine_options = {
    "pool_pre_ping": True,
    "echo": False,
}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    engine_options.update({"pool_size": 10, "max_overflow": 20})

engine = create_engine(settings.DATABASE_URL, **engine_options)

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
        plan_execution_event,
        user_feedback,
        pantry_item,
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
        if "activity_level" not in columns:
            with engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE profiles ADD COLUMN activity_level VARCHAR(20) "
                    "NOT NULL DEFAULT 'moderate'"
                ))

    # create_all only creates absent tables; it never upgrades an existing one.
    # Fail before accepting requests when application models outpace migrations.
    from app.models.meal_plan import MealPlan

    plan_columns = {column["name"] for column in inspect(engine).get_columns("meal_plans")}
    required_columns = set(MealPlan.__table__.columns.keys())
    missing = sorted(required_columns - plan_columns)
    if missing:
        raise RuntimeError(
            "meal_plans 数据库结构落后，缺少列 "
            + ", ".join(missing)
            + "；请先执行 alembic upgrade head"
        )
    from app.models.plan_execution_event import PlanExecutionEvent

    execution_columns = {column["name"] for column in inspect(engine).get_columns("plan_execution_events")}
    missing_execution = sorted(set(PlanExecutionEvent.__table__.columns.keys()) - execution_columns)
    if missing_execution:
        raise RuntimeError(
            "plan_execution_events 数据库结构落后，缺少列 "
            + ", ".join(missing_execution)
            + "；请先执行 alembic upgrade head"
        )
