"""Non-RAG administrator CRUD and authorization acceptance tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models import Ingredient, IngredientNutrition, Recipe, RecipeIngredient, User
from app.services.security import get_current_user


@pytest.fixture
def admin_api():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as db:
        admin = User(
            email="admin@example.test",
            nickname="Admin",
            password_hash="hash",
            role="admin",
        )
        member = User(
            email="member@example.test",
            nickname="Member",
            password_hash="hash",
            role="user",
        )
        ingredient = Ingredient(
            name="番茄",
            category="vegetable",
            unit="g",
            unit_price=0.04,
            storage_days=5,
        )
        db.add_all([admin, member, ingredient])
        db.flush()
        db.add(
            IngredientNutrition(
                ingredient_id=ingredient.ingredient_id,
                calories_per_100g=18,
                protein_per_100g=0.9,
                fat_per_100g=0.2,
                carbs_per_100g=3.9,
                fiber_per_100g=1.2,
            )
        )
        recipe = Recipe(
            name="番茄小食",
            category="light_meal",
            cuisine_type="chinese",
            difficulty="easy",
            prep_time=5,
            cook_time=3,
            servings=1,
            steps=[{"step": 1, "content": "切块装盘"}],
        )
        db.add(recipe)
        db.flush()
        db.add(
            RecipeIngredient(
                recipe_id=recipe.recipe_id,
                ingredient_id=ingredient.ingredient_id,
                quantity=150,
                unit="g",
                is_optional=0,
            )
        )
        db.commit()
        ids = {
            "admin": admin.user_id,
            "member": member.user_id,
            "ingredient": ingredient.ingredient_id,
            "recipe": recipe.recipe_id,
        }

    current = {"id": ids["admin"]}

    def override_db():
        with session_factory() as db:
            yield db

    def override_user():
        with session_factory() as db:
            return db.get(User, current["id"])

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    try:
        yield TestClient(app), current, ids
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def ingredient_payload(name="燕麦"):
    return {
        "name": name,
        "category": "grain",
        "unit": "g",
        "unit_price": 0.03,
        "season_tags": None,
        "storage_days": 120,
        "nutrition": {
            "calories": 379,
            "protein": 13.2,
            "fat": 6.5,
            "carbs": 67.7,
            "fiber": 10.1,
        },
    }


def recipe_payload(ingredient_id, name="烤燕麦杯"):
    return {
        "name": name,
        "description": "适合早餐的简单主食",
        "category": "staple",
        "cuisine_type": "western",
        "difficulty": "easy",
        "prep_time": 5,
        "cook_time": 20,
        "servings": 1,
        "steps": [{"step": 1, "content": "混合食材并烘烤"}],
        "image_url": None,
        "nutrition": {
            "calories": 320,
            "protein": 12,
            "fat": 8,
            "carbs": 48,
            "fiber": 6,
        },
        "tags": ["早餐", "高纤维"],
        "ingredients": [
            {
                "ingredient_id": ingredient_id,
                "quantity": 80,
                "unit": "g",
                "is_optional": False,
            }
        ],
    }


def test_non_admin_cannot_read_or_write_admin_resources(admin_api):
    client, current, ids = admin_api
    current["id"] = ids["member"]

    assert client.get("/api/v1/admin/overview").status_code == 403
    assert client.get("/api/v1/admin/ingredients").status_code == 403
    assert client.post("/api/v1/admin/ingredients", json=ingredient_payload()).status_code == 403
    assert client.post(
        "/api/v1/admin/recipes",
        json=recipe_payload(ids["ingredient"]),
    ).status_code == 403


def test_admin_overview_returns_counts_without_private_user_data(admin_api):
    client, _, _ = admin_api

    response = client.get("/api/v1/admin/overview")
    assert response.status_code == 200
    assert response.json() == {
        "users": 2,
        "profiles": 0,
        "recipes": 1,
        "ingredients": 1,
        "plans": 0,
    }
    assert "email" not in response.text


def test_admin_ingredient_crud_and_referenced_delete_conflict(admin_api):
    client, _, ids = admin_api

    created = client.post("/api/v1/admin/ingredients", json=ingredient_payload())
    assert created.status_code == 201
    ingredient_id = created.json()["ingredient_id"]
    assert created.json()["nutrition"]["fiber"] == 10.1

    payload = ingredient_payload("全谷燕麦")
    payload["unit_price"] = 0.05
    updated = client.put(f"/api/v1/admin/ingredients/{ingredient_id}", json=payload)
    assert updated.status_code == 200
    assert updated.json()["name"] == "全谷燕麦"
    assert updated.json()["unit_price"] == 0.05

    conflict = client.delete(f"/api/v1/admin/ingredients/{ids['ingredient']}")
    assert conflict.status_code == 409
    assert client.delete(f"/api/v1/admin/ingredients/{ingredient_id}").status_code == 204


def test_admin_recipe_crud_and_input_integrity(admin_api):
    client, _, ids = admin_api
    payload = recipe_payload(ids["ingredient"])

    unknown = recipe_payload(999999, "未知食材菜谱")
    assert client.post("/api/v1/admin/recipes", json=unknown).status_code == 422

    duplicate = recipe_payload(ids["ingredient"], "重复食材菜谱")
    duplicate["ingredients"].append(dict(duplicate["ingredients"][0]))
    assert client.post("/api/v1/admin/recipes", json=duplicate).status_code == 422

    created = client.post("/api/v1/admin/recipes", json=payload)
    assert created.status_code == 201
    recipe_id = created.json()["recipe_id"]
    detail = client.get(f"/api/v1/recipes/{recipe_id}")
    assert detail.status_code == 200
    assert detail.json()["ingredients"][0]["ingredient_id"] == ids["ingredient"]

    payload["name"] = "肉桂烤燕麦杯"
    payload["steps"].append({"step": 2, "content": "稍凉后食用"})
    updated = client.put(f"/api/v1/admin/recipes/{recipe_id}", json=payload)
    assert updated.status_code == 200
    assert client.get(f"/api/v1/recipes/{recipe_id}").json()["name"] == "肉桂烤燕麦杯"

    assert client.delete(f"/api/v1/admin/recipes/{recipe_id}").status_code == 204
    assert client.get(f"/api/v1/recipes/{recipe_id}").status_code == 404


def test_recipe_pagination_contract_and_missing_recipe(admin_api):
    client, _, ids = admin_api

    page = client.get("/api/v1/recipes?page=1&page_size=1")
    assert page.status_code == 200
    assert page.json()["total"] == 1
    assert page.json()["page"] == 1
    assert page.json()["page_size"] == 1
    assert len(page.json()["items"]) == 1
    assert client.get(f"/api/v1/recipes/{ids['recipe'] + 9999}").status_code == 404
