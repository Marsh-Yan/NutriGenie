"""Real-MySQL V2.1 migration and concurrency checks in an isolated schema."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import Base
from app import models  # noqa: F401 - register all tables before creating the legacy baseline
from app.models.meal_plan import MealPlan
from app.models.plan_execution_event import PlanExecutionEvent
from app.models.profile import Profile
from app.models.user import User


@pytest.mark.integration
def test_mysql_v21_migration_and_execution_uniqueness():
    url = make_url(settings.DATABASE_URL)
    if not url.drivername.startswith("mysql"):
        pytest.skip("requires MySQL configuration")

    # CREATE without IF NOT EXISTS means cleanup can only target a schema made here.
    schema = f"nutrigenie_phase_f_{uuid4().hex[:12]}"
    admin_engine = create_engine(url.set(database=None), isolation_level="AUTOCOMMIT")
    test_url = url.set(database=schema)
    created = False
    test_engine = None
    previous_override = settings.DATABASE_URL_OVERRIDE
    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f"CREATE DATABASE `{schema}` CHARACTER SET utf8mb4"))
            created = True

        test_engine = create_engine(test_url)
        Base.metadata.create_all(test_engine)
        with Session(test_engine) as session:
            user = User(email="verify@example.com", nickname="验收", password_hash="not-used")
            session.add(user)
            session.flush()
            profile = Profile(
                user_id=user.user_id, age=30, gender="female", height=165, weight=60,
                diet_type="balanced", health_goal="healthy",
            )
            session.add(profile)
            session.flush()
            plan = MealPlan(profile_id=profile.profile_id, user_input="验证", duration_days=7, total_budget=300)
            session.add(plan)
            session.commit()
            plan_id, user_id, profile_id = plan.plan_id, user.user_id, profile.profile_id

        # Model bootstrap is V2.1; remove only V2.1 objects in this disposable schema
        # to exercise the actual ALTER/CREATE path against existing user data.
        foreign_keys = inspect(test_engine).get_foreign_keys("meal_plans")
        with test_engine.begin() as connection:
            for table in ("pantry_items", "user_feedback", "plan_execution_events"):
                connection.execute(text(f"DROP TABLE `{table}`"))
            for key in foreign_keys:
                if key["constrained_columns"] == ["source_plan_id"]:
                    connection.execute(text(f"ALTER TABLE meal_plans DROP FOREIGN KEY `{key['name']}`"))
            for column in ("title", "archived_at", "source_plan_id"):
                connection.execute(text(f"ALTER TABLE meal_plans DROP COLUMN `{column}`"))
            connection.execute(text("ALTER TABLE profiles DROP COLUMN activity_level"))

        settings.DATABASE_URL_OVERRIDE = test_url.render_as_string(hide_password=False)
        alembic = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        alembic.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
        command.upgrade(alembic, "head")
        inspector = inspect(test_engine)
        assert "activity_level" in {column["name"] for column in inspector.get_columns("profiles")}
        assert {"title", "archived_at", "source_plan_id"} <= {
            column["name"] for column in inspector.get_columns("meal_plans")
        }
        assert {"plan_execution_events", "user_feedback", "pantry_items"} <= set(inspector.get_table_names())
        assert any(
            set(constraint["column_names"]) == {"plan_id", "day", "meal_slot"}
            for constraint in inspector.get_unique_constraints("plan_execution_events")
        )

        with test_engine.connect() as connection:
            assert connection.scalar(text("SELECT activity_level FROM profiles WHERE profile_id = :id"), {"id": profile_id}) == "moderate"

        barrier = Barrier(2)

        def write_same_slot(status: str) -> str:
            with Session(test_engine) as session:
                session.add(PlanExecutionEvent(
                    plan_id=plan_id, user_id=user_id, day=1, meal_slot="breakfast", status=status,
                ))
                barrier.wait(timeout=10)
                try:
                    session.commit()
                    return "saved"
                except IntegrityError:
                    session.rollback()
                    return "duplicate"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(write_same_slot, ("completed", "skipped")))
        assert sorted(results) == ["duplicate", "saved"]
        with test_engine.connect() as connection:
            assert connection.scalar(text("SELECT COUNT(*) FROM plan_execution_events")) == 1
    finally:
        settings.DATABASE_URL_OVERRIDE = previous_override
        if test_engine is not None:
            test_engine.dispose()
        if created:
            with admin_engine.connect() as connection:
                connection.execute(text(f"DROP DATABASE `{schema}`"))
        admin_engine.dispose()
