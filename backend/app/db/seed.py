"""种子数据导入脚本

用法: python -m app.db.seed
"""

import json
import os
from datetime import datetime

from app.db.database import SessionLocal, init_db
from app.models.profile import Profile
from app.models.recipe import Recipe
from app.models.ingredient import Ingredient
from app.models.ingredient_nutrition import IngredientNutrition
from app.models.recipe_ingredient import RecipeIngredient


SEED_DIR = os.path.join(os.path.dirname(__file__), "seed_data")


def load_json(filename: str) -> list:
    filepath = os.path.join(SEED_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_profiles():
    """创建默认用户画像（仅用于开发测试）"""
    session = SessionLocal()
    try:
        existing = session.query(Profile).first()
        if existing:
            print("[SKIP] profiles 已有数据，跳过")
            return

        profile = Profile(
            age=28,
            gender="male",
            height=175.0,
            weight=72.0,
            activity_level="moderate",
            diet_type="balanced",
            health_goal="fat_loss",
            allergies=["海鲜"],
            daily_budget=50.0,
        )
        session.add(profile)
        session.commit()
        print(f"[OK] 创建默认用户画像 (profile_id={profile.profile_id})")
    finally:
        session.close()


def seed_ingredients():
    session = SessionLocal()
    try:
        data = load_json("ingredients.json")
        existing_ids = {
            row[0] for row in session.query(Ingredient.ingredient_id).all()
        }
        missing = [item for item in data if item["ingredient_id"] not in existing_ids]
        for item in missing:
            session.add(Ingredient(**item))
        session.commit()
        if missing:
            print(f"[OK] 新增 {len(missing)} 种食材（目录共 {len(data)} 种）")
        else:
            print(f"[SKIP] 食材目录已完整（共 {len(data)} 种）")
    finally:
        session.close()


def seed_ingredient_nutrition():
    session = SessionLocal()
    try:
        data = load_json("ingredient_nutrition.json")
        existing_ids = {
            row[0] for row in session.query(IngredientNutrition.ingredient_id).all()
        }
        missing = [item for item in data if item["ingredient_id"] not in existing_ids]
        for item in missing:
            session.add(IngredientNutrition(**item))
        session.commit()
        if missing:
            print(f"[OK] 新增 {len(missing)} 条营养数据（目录共 {len(data)} 条）")
        else:
            print(f"[SKIP] 营养目录已完整（共 {len(data)} 条）")
    finally:
        session.close()


def seed_recipes():
    session = SessionLocal()
    try:
        if session.query(Recipe).first():
            print("[SKIP] recipes 已有数据，跳过")
            return

        data = load_json("recipes.json")
        for item in data:
            session.add(Recipe(**item))
        session.commit()
        print(f"[OK] 导入 {len(data)} 道菜谱")
    finally:
        session.close()


def seed_recipe_ingredients():
    session = SessionLocal()
    try:
        if session.query(RecipeIngredient).first():
            print("[SKIP] recipe_ingredients 已有数据，跳过")
            return

        data = load_json("recipe_ingredients.json")
        for item in data:
            session.add(RecipeIngredient(**item))
        session.commit()
        print(f"[OK] 导入 {len(data)} 条菜谱-食材关联")
    finally:
        session.close()


def seed_all():
    """执行全量数据导入"""
    print("=" * 50)
    print("NutriGenie 种子数据导入开始")
    print("=" * 50)

    print("\n[0/6] 初始化数据库表...")
    init_db()
    print("[OK] 表创建完成")

    print("\n[1/6] 导入食材...")
    seed_ingredients()

    print("\n[2/6] 导入食材营养数据...")
    seed_ingredient_nutrition()

    print("\n[3/6] 导入菜谱...")
    seed_recipes()

    print("\n[4/6] 导入菜谱-食材关联...")
    seed_recipe_ingredients()

    print("\n[5/6] 创建默认用户画像...")
    seed_profiles()

    print("\n[6/6] 验证数据...")
    verify_data()

    print("\n" + "=" * 50)
    print("种子数据导入完成!")
    print("=" * 50)


def verify_data():
    """验证导入数据完整性"""
    session = SessionLocal()
    try:
        ingredients = session.query(Ingredient).count()
        nutrition = session.query(IngredientNutrition).count()
        recipes = session.query(Recipe).count()
        rels = session.query(RecipeIngredient).count()
        profiles = session.query(Profile).count()
        ingredients_without_nutrition = (
            session.query(Ingredient)
            .outerjoin(
                IngredientNutrition,
                IngredientNutrition.ingredient_id == Ingredient.ingredient_id,
            )
            .filter(IngredientNutrition.ingredient_id.is_(None))
            .count()
        )

        print(f"  食材: {ingredients} 种")
        print(f"  营养数据: {nutrition} 条")
        print(f"  菜谱: {recipes} 道")
        print(f"  菜谱-食材关联: {rels} 条")
        print(f"  用户画像: {profiles} 个")
        print(f"  缺少营养数据的食材: {ingredients_without_nutrition} 种")

        if all([ingredients > 0, nutrition > 0, recipes > 0, rels > 0]) and ingredients_without_nutrition == 0:
            print("[OK] 数据完整性验证通过")
        else:
            print("[WARN] 部分数据为空，请检查")

    finally:
        session.close()


if __name__ == "__main__":
    seed_all()
