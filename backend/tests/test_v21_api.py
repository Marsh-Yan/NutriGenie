"""V2.1 ownership, persistence, compatibility and replacement tests."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db.database import Base, get_db
from app.main import app
from app.models import Ingredient, MealPlan, MealPlanVersion, Profile, Recipe, User
from app.services.security import get_current_user


@pytest.fixture
def api(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as db:
        first = User(email="a@example.test", nickname="A", password_hash="hash", role="user")
        second = User(email="b@example.test", nickname="B", password_hash="hash", role="user")
        db.add_all([first, second])
        db.flush()
        profile = Profile(user_id=first.user_id, age=30, gender="female", height=165, weight=60, activity_level="moderate", diet_type="balanced", health_goal="healthy", daily_budget=50)
        db.add(profile)
        db.flush()
        plan = MealPlan(profile_id=profile.profile_id, user_input="健康饮食", duration_days=1, total_budget=100, status="completed", result_json={
            "weekly_plan": [{"day": 1, "meals": {"breakfast": {"name": "A"}, "lunch": {"name": "B"}, "dinner": {"name": "C"}}}],
        })
        ingredient = Ingredient(name="番茄", category="vegetable", unit="g", unit_price=0.1)
        recipe = Recipe(name="番茄菜", category="main_dish", cuisine_type="chinese", difficulty="easy", prep_time=5, cook_time=5, steps=[{"step": 1, "content": "做菜"}])
        db.add_all([plan, ingredient, recipe])
        db.commit()
        ids = (first.user_id, second.user_id, plan.plan_id, ingredient.ingredient_id, recipe.recipe_id)

    current = {"id": ids[0]}
    def override_db():
        with session_factory() as db:
            yield db
    def override_user():
        with session_factory() as db:
            return db.get(User, current["id"])
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    try:
        client = TestClient(app)
        yield client, current, ids, session_factory
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_plan_index_metadata_and_ownership(api):
    client, current, ids, _ = api
    plan_id = ids[2]
    legacy = client.get("/api/v1/plans")
    assert legacy.status_code == 200 and isinstance(legacy.json(), list)
    page = client.get("/api/v1/plans?page=1&page_size=10")
    assert page.status_code == 200 and page.json()["total"] == 1
    assert page.json()["items"][0]["title"] == "1 天饮食计划"
    assert client.patch(f"/api/v1/plans/{plan_id}", json={"archived": None}).status_code == 422
    updated = client.patch(f"/api/v1/plans/{plan_id}", json={"title": "工作日", "archived": True})
    assert updated.status_code == 200 and updated.json()["title"] == "工作日"
    assert len(client.get("/api/v1/plans").json()) == 1
    assert client.get("/api/v1/plans?page=1").json()["total"] == 0
    assert client.get("/api/v1/plans?archived=true").json()["total"] == 1
    current["id"] = ids[1]
    assert client.patch(f"/api/v1/plans/{plan_id}", json={"title": "越权"}).status_code == 404
    assert client.get(f"/api/v1/plans/{plan_id}/execution").status_code == 404
    assert client.post(f"/api/v1/plans/{plan_id}/clone", json={}).status_code == 404
    assert client.post(f"/api/v1/plans/{plan_id}/meals/1/lunch/replace", json={}).status_code == 404


def test_clone_is_new_run_without_copying_result(api, monkeypatch):
    client, _, ids, session_factory = api
    def fake_enqueue(db, clone):
        from app.models.meal_plan_run import MealPlanRun
        run = MealPlanRun(plan_id=clone.plan_id, status="pending")
        db.add(run)
        db.commit()
        db.refresh(run)
        return run
    monkeypatch.setattr("app.api.routes.plans.enqueue_initial_plan", fake_enqueue)
    response = client.post(f"/api/v1/plans/{ids[2]}/clone", json={"title": "下周", "overrides": {"total_budget": 120}})
    assert response.status_code == 202
    with session_factory() as db:
        clone = db.get(MealPlan, response.json()["plan_id"])
        assert clone.source_plan_id == ids[2]
        assert clone.title == "下周" and float(clone.total_budget) == 120
        assert clone.result_json is None and clone.status == "pending"


def test_execution_upsert_and_invalid_slot(api):
    client, current, ids, session_factory = api
    url = f"/api/v1/plans/{ids[2]}/execution"
    payload = {"events": [{"day": 1, "meal_slot": "breakfast", "status": "completed", "note": None}]}
    assert client.put(url, json=payload).status_code == 200
    payload["events"][0]["status"] = "adjusted"
    assert client.put(url, json=payload).json()["events"][0]["status"] == "adjusted"
    with session_factory() as db:
        from app.models.plan_execution_event import PlanExecutionEvent
        assert db.query(PlanExecutionEvent).count() == 1
    assert client.put(url, json={"events": [{"day": 2, "meal_slot": "lunch", "status": "completed"}]}).status_code == 422
    current["id"] = ids[1]
    assert client.put(url, json=payload).status_code == 404


def test_feedback_and_pantry_are_owned(api):
    client, current, ids, _ = api
    assert client.post("/api/v1/feedback", json={"plan_id": ids[2], "feedback_type": "too_slow", "rating": 2}).status_code == 201
    created = client.post("/api/v1/pantry/items", json={"ingredient_id": ids[3], "quantity": 0.5, "unit": "kg"})
    assert created.status_code == 201
    item_id = created.json()["pantry_item_id"]
    assert created.json()["quantity"] == 500 and created.json()["unit"] == "g"
    assert client.post("/api/v1/pantry/items", json={"ingredient_id": ids[3], "quantity": 1, "unit": "g"}).status_code == 409
    assert client.post("/api/v1/pantry/items", json={"ingredient_id": ids[3], "quantity": 1, "unit": "个"}).status_code == 422
    assert client.put(f"/api/v1/pantry/items/{item_id}", json={"quantity": 2, "unit": "kg"}).json()["quantity"] == 2000
    current["id"] = ids[1]
    assert client.get("/api/v1/pantry").json()["items"] == []
    assert client.put(f"/api/v1/pantry/items/{item_id}", json={"quantity": 1}).status_code == 404
    assert client.delete(f"/api/v1/pantry/items/{item_id}").status_code == 404
    assert client.post("/api/v1/feedback", json={"plan_id": ids[2], "feedback_type": "liked"}).status_code == 404
    current["id"] = ids[0]
    assert client.delete(f"/api/v1/pantry/items/{item_id}").status_code == 204


def test_replacement_fails_closed_without_valid_candidate(api):
    client, _, ids, _ = api
    response = client.post(f"/api/v1/plans/{ids[2]}/meals/1/dinner/replace", json={"reason": "too_expensive"})
    assert response.status_code == 409


def test_replacement_creates_immutable_validated_version(api):
    from app.services.ai_plan_models import GeneratedPlan
    from app.services.ingredient_catalog import load_seed_catalog, normalize_generated_plan
    from app.services.plan_aggregator import aggregate_generated_plan
    from app.services.plan_validator import validate_plan

    client, _, ids, session_factory = api
    plan = GeneratedPlan.model_validate({
        "recipes": [{
            "name": f"番茄创意料理 {index}", "meal_slots": ["breakfast", "lunch", "dinner"],
            "ingredients": [{"name": "西红柿", "quantity": 120, "unit": "g"}, {"name": "鸡蛋", "quantity": 1, "unit": "个"}],
            "steps": ["处理食材", "完成烹饪"],
        } for index in range(5)],
        "meals": [
            {"day": day, "slot": slot, "recipe_index": index}
            for index, (day, slot) in enumerate([
                (1, "breakfast"), (1, "lunch"), (1, "dinner"),
                (2, "breakfast"), (2, "lunch"), (2, "dinner"),
            ])
        ],
    })
    plan.meals[-1].recipe_index = 0
    normalized = normalize_generated_plan(plan, load_seed_catalog()).plan
    constraints = {"allergen_names": [], "diet_type": "balanced", "total_budget": 0}
    intent = {"meal_count_per_day": 3}
    validation = validate_plan(normalized, constraints, intent=intent, duration_days=2, require_resolved=True, enforce_diversity=True, enforce_quality_targets=True)
    assert validation.passed
    original = aggregate_generated_plan(normalized, validation, duration_days=2, intent=intent, constraints=constraints)
    with session_factory() as db:
        saved = db.get(MealPlan, ids[2])
        saved.duration_days = 2
        saved.total_budget = 0
        saved.result_json = original
        version = MealPlanVersion(plan_id=saved.plan_id, version_no=1, result_json=original, validation_json=original["validation"])
        db.add(version)
        db.flush()
        saved.current_version_id = version.version_id
        db.commit()
        old_version_id = version.version_id
    response = client.post(f"/api/v1/plans/{ids[2]}/meals/2/dinner/replace", json={"reason": "other"})
    assert response.status_code == 200, response.text
    assert response.json()["plan_validation"]["passed"] is True
    assert response.json()["version_id"] != old_version_id
    with session_factory() as db:
        old = db.get(MealPlanVersion, old_version_id)
        saved = db.get(MealPlan, ids[2])
        current_version = db.get(MealPlanVersion, saved.current_version_id)
        assert old.result_json == original
        assert saved.current_version_id == response.json()["version_id"]
        assert current_version.result_json["version_id"] == current_version.version_id
        assert saved.result_json["version_id"] == current_version.version_id
        assert db.query(MealPlanVersion).filter_by(plan_id=ids[2]).count() == 2
    rejected = client.post(f"/api/v1/plans/{ids[2]}/meals/2/dinner/replace", json={"reason": "too_slow"})
    assert rejected.status_code == 409
    with session_factory() as db:
        profile = db.get(Profile, db.get(MealPlan, ids[2]).profile_id)
        profile.allergies = ["鸡蛋"]
        db.commit()
    rejected_allergen = client.post(f"/api/v1/plans/{ids[2]}/meals/2/dinner/replace", json={"reason": "other"})
    assert rejected_allergen.status_code == 409
    with session_factory() as db:
        assert db.query(MealPlanVersion).filter_by(plan_id=ids[2]).count() == 2


def test_migration_upgrades_legacy_snapshot(tmp_path, monkeypatch):
    db_file = tmp_path / "legacy.db"
    url = f"sqlite:///{db_file.as_posix()}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE users (user_id INTEGER PRIMARY KEY, email VARCHAR(255), nickname VARCHAR(50), password_hash VARCHAR(255))")
        connection.exec_driver_sql("CREATE TABLE profiles (profile_id INTEGER PRIMARY KEY, user_id INTEGER, age INTEGER)")
        connection.exec_driver_sql("CREATE TABLE meal_plans (plan_id INTEGER PRIMARY KEY, profile_id INTEGER, created_at DATETIME)")
        connection.exec_driver_sql("CREATE TABLE ingredients (ingredient_id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql("CREATE TABLE recipes (recipe_id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql("INSERT INTO profiles (profile_id, user_id, age) VALUES (1, 1, 30)")
        connection.exec_driver_sql("INSERT INTO meal_plans (plan_id, profile_id, created_at) VALUES (1, 1, CURRENT_TIMESTAMP)")
    monkeypatch.setattr(settings, "DATABASE_URL_OVERRIDE", url)
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    command.upgrade(config, "head")
    assert {column["name"] for column in inspect(engine).get_columns("meal_plans")} >= {"title", "source_plan_id", "archived_at"}
    assert "pantry_items" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT activity_level FROM profiles WHERE profile_id=1")).scalar_one() == "moderate"
        assert connection.execute(text("SELECT plan_id FROM meal_plans WHERE plan_id=1")).scalar_one() == 1
    command.downgrade(config, "20260919_0005")
    assert "pantry_items" not in inspect(engine).get_table_names()
    engine.dispose()


def test_migration_upgrade_after_fresh_bootstrap(tmp_path, monkeypatch):
    db_file = tmp_path / "fresh.db"
    url = f"sqlite:///{db_file.as_posix()}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "DATABASE_URL_OVERRIDE", url)
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    command.upgrade(config, "head")
    assert "pantry_items" in inspect(engine).get_table_names()
    engine.dispose()
