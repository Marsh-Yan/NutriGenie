"""数据验证脚本

运行: python -m app.db.verify
"""

import sys

# Windows PowerShell 可能默认使用 GBK，无法输出人民币符号等种子数据字符。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.db.database import SessionLocal
from app.services.recipe_service import get_recipes, get_recipe, get_recipe_ingredients
from app.services.ingredient_service import get_ingredients
from app.services.profile_service import get_profile


def verify():
    print("=" * 50)
    print("NutriGenie 数据服务验证")
    print("=" * 50)

    db = SessionLocal()
    try:
        # 1. 查询菜谱列表
        print("\n[1] 菜谱列表 (page=1, page_size=5):")
        recipes, total = get_recipes(db, page=1, page_size=5)
        print(f"    总数: {total}, 返回: {len(recipes)}")
        for r in recipes:
            print(f"    - [{r.recipe_id}] {r.name} ({r.cuisine_type})")

        # 2. 查询菜谱详情
        print(f"\n[2] 菜谱详情 (recipe_id=1):")
        recipe = get_recipe(db, 1)
        if recipe:
            print(f"    名称: {recipe.name}")
            print(f"    分类: {recipe.category} / {recipe.cuisine_type}")
            print(f"    时间: {recipe.prep_time}+{recipe.cook_time}min")
            print(f"    营养: {recipe.total_calories}kcal, P{recipe.total_protein}g")
            print(f"    步骤数: {len(recipe.steps)}")
            print(f"    标签: {recipe.tags}")

        # 3. 查询菜谱食材
        print(f"\n[3] 菜谱食材 (recipe_id=1):")
        ingredients = get_recipe_ingredients(db, 1)
        for ing in ingredients:
            print(f"    - {ing['name']} x{ing['quantity']}{ing['unit']} "
                  f"≈ ¥{ing['estimated_cost']}")

        # 4. 食材列表
        print(f"\n[4] 食材列表 (category=vegetable):")
        veg_list, veg_total = get_ingredients(db, category="vegetable")
        print(f"    蔬菜类: {veg_total} 种")
        for v in veg_list[:5]:
            nut = v["nutrition_per_100g"]
            print(f"    - {v['name']} ¥{v['unit_price']}/{v['unit']} "
                  f"({nut['calories']}kcal/100g)")

        # 5. 用户画像
        print(f"\n[5] 默认用户画像:")
        profile = get_profile(db, 1)
        if profile:
            print(f"    ID: {profile.profile_id}, 性别: {profile.gender}")
            print(f"    身高: {profile.height}cm, 体重: {profile.weight}kg")
            print(f"    目标: {profile.health_goal}")
            print(f"    过敏: {profile.allergies}")

        print("\n" + "=" * 50)
        print("所有服务验证通过!")
        print("=" * 50)

    finally:
        db.close()


if __name__ == "__main__":
    verify()
