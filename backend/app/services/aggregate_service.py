"""聚合排序与周计划生成

将推荐引擎的排序结果 → TOP5 + 周计划 + 营养报告 + 采购清单 + 总结
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.services.constraint_analyzer import ConstraintSet
from app.services.recommendation_engine import (
    ScoredRecipe,
    rank_candidates,
    RecipeCandidate,
    build_candidate_pool,
    score_candidate,
    DEFAULT_WEIGHTS,
)
from app.services.scoring import variety_score
from app.services.recipe_service import get_recipe_ingredients
from app.services.nutrition_service import calculate_recipe_nutrition
from app.services.cost_service import (
    DISCRETE_PURCHASE_UNITS,
    convert_quantity,
)

BUDGET_UTILIZATION_MIN = 0.80

# ─── 每餐的菜谱分类偏好 ─────────────────────────

MEAL_SLOT_CATEGORIES = {
    "breakfast": {"light_meal", "staple"},
    "lunch": {"main_dish", "side_dish", "soup"},
    "dinner": {"main_dish", "side_dish", "soup", "light_meal"},
}

MEAL_SLOT_NAMES = {
    "breakfast": "早餐",
    "lunch": "午餐",
    "dinner": "晚餐",
}

MEAL_CALORIE_RATIOS = {"breakfast": 0.25, "lunch": 0.40, "dinner": 0.35}
MEAL_MAX_SERVINGS = {"breakfast": 1, "lunch": 2, "dinner": 2}
BREAKFAST_UNSUITABLE_KEYWORDS = ("炒饭", "牛排", "意面", "pasta", "steak")


@dataclass
class WeeklyPlanResult:
    """完整规划结果 — 直接对应 API 的 PlanResult"""

    top5: List[dict]
    weekly_plan: List[dict]
    nutrition_report: dict
    shopping_list: dict
    summary: str


def _build_top5(
    ranked: List[ScoredRecipe],
    constraints: ConstraintSet,
) -> List[dict]:
    """从排序结果中提取 TOP5 展示数据

    每道菜包含：评分明细、营养、成本、推荐理由
    """
    top5 = ranked[:5]
    result = []

    for r in top5:
        # 生成简短推荐理由
        explanation_parts = []
        if r.scores["health"] >= 0.8:
            explanation_parts.append("热量匹配")
        if r.scores["budget"] >= 0.8:
            explanation_parts.append("预算友好")
        if r.scores["season"] >= 0.8:
            explanation_parts.append("时令食材")
        if r.scores["preference"] >= 0.7:
            explanation_parts.append("符合口味")
        if r.scores["utilization"] >= 0.5:
            explanation_parts.append("可复用已有食材")

        if not explanation_parts:
            explanation_parts.append("综合推荐")

        explanation = f"{r.name}：{'、'.join(explanation_parts)}。"

        result.append({
            "recipe_id": r.recipe_id,
            "name": r.name,
            "image_url": r.image_url,
            "category": r.category,
            "cuisine_type": r.cuisine_type,
            "difficulty": r.difficulty,
            "prep_time": r.prep_time,
            "cook_time": r.cook_time,
            "scores": {
                "health": round(r.scores["health"], 2),
                "budget": round(r.scores["budget"], 2),
                "preference": round(r.scores["preference"], 2),
                "season": round(r.scores["season"], 2),
                "variety": round(r.scores["variety"], 2),
                "utilization": round(r.scores["utilization"], 2),
            },
            "total_score": round(r.total_score, 2),
            "nutrition": {
                "calories": r.total_calories,
                "protein": 0,
                "fat": 0,
                "carbs": 0,
                "fiber": 0,
            },
            "estimated_cost": r.estimated_cost,
            "explanation": explanation,
            "evidence": r.evidence,
        })

    return result


def _greedy_weekly_plan(
    db: Session,
    candidates_pool: List[RecipeCandidate],
    ranked: List[ScoredRecipe],
    constraints: ConstraintSet,
    current_season: str,
    owned_ids: List[int],
    weights: Dict[str, float],
    duration_days: int = 7,
    meal_count_per_day: int = 3,
    owned_recipes_map: Dict[int, RecipeCandidate] = None,
) -> Tuple[List[dict], int]:
    """贪心算法生成周计划

    逐天逐餐选择最优菜谱，每次选择后更新 variety_score。
    breakfast 优先选 light_meal/staple，lunch/dinner 优先选 main_dish。

    Returns:
        (weekly_plan, total_days_used)
    """
    # 已选记录，用于 variety_score 动态计算
    already_selected: List[dict] = []

    # 排名靠前的菜谱优先选择（按总分排序）
    # 但每月餐需要重新评分（variety 动态变化）
    scored_map = {r.recipe_id: r for r in ranked}
    candidate_map = owned_recipes_map or {}
    if not candidate_map:
        candidate_map = {c.recipe_id: c for c in candidates_pool}

    weekly_plan = []
    total_cost = 0.0

    # 跟踪每道菜在本周的使用次数
    recipe_usage_count: Dict[int, int] = {}

    for day in range(1, duration_days + 1):
        day_meals = {}
        day_nutrition = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}

        meal_slots = {
            1: ["dinner"],
            2: ["lunch", "dinner"],
            3: ["breakfast", "lunch", "dinner"],
        }[max(1, min(meal_count_per_day, 3))]
        for meal_slot in meal_slots:
            preferred_cats = MEAL_SLOT_CATEGORIES[meal_slot]
            best_recipe = None
            best_score = -1.0

            # 遍历候选菜谱（按总分降序），找最优
            for scored in ranked:
                candidate = candidate_map.get(scored.recipe_id)
                if not candidate:
                    continue

                # 排除早餐不合适的主菜
                if candidate.category not in preferred_cats:
                    continue
                if meal_slot == "breakfast" and any(
                    keyword in candidate.name.lower()
                    for keyword in BREAKFAST_UNSUITABLE_KEYWORDS
                ):
                    continue

                # 计算 variety_score（基于已选列表）
                v = variety_score(
                    recipe_id=scored.recipe_id,
                    recipe_category=candidate.category,
                    cuisine_type=candidate.cuisine_type,
                    already_selected=already_selected,
                )

                # 加权总分（variety 实时更新）
                total = (
                    weights["health"] * scored.scores["health"]
                    + weights["budget"] * scored.scores["budget"]
                    + weights["preference"] * scored.scores["preference"]
                    + weights.get("semantic", 0.0) * scored.scores.get("semantic", 0.0)
                    + weights["season"] * scored.scores["season"]
                    + weights["variety"] * v
                    + weights["utilization"] * scored.scores["utilization"]
                )

                if total > best_score:
                    best_score = total
                    best_recipe = scored

            # 没找到合适菜谱（理论上不可能，兜底）
            if not best_recipe:
                continue

            # 记录选择
            already_selected.append({
                "recipe_id": best_recipe.recipe_id,
                "category": candidate_map[best_recipe.recipe_id].category,
                "cuisine_type": best_recipe.cuisine_type,
                "day": day,
                "meal_slot": meal_slot,
            })

            recipe_usage_count[best_recipe.recipe_id] = (
                recipe_usage_count.get(best_recipe.recipe_id, 0) + 1
            )

            total_cost += best_recipe.estimated_cost

            meal_data = {
                "recipe_id": best_recipe.recipe_id,
                "name": best_recipe.name,
                "serving_size": 1,
                "nutrition": {
                    "calories": best_recipe.total_calories,
                    "protein": 0,
                    "fat": 0,
                    "carbs": 0,
                },
            }
            day_meals[meal_slot] = meal_data

            # 累加日营养（约数，详细营养后续计算）
            day_nutrition["calories"] += best_recipe.total_calories

        weekly_plan.append({
            "day": day,
            "meals": {
                "breakfast": day_meals.get("breakfast"),
                "lunch": day_meals.get("lunch"),
                "dinner": day_meals.get("dinner"),
            },
            "total_nutrition": {
                k: round(v, 1) for k, v in day_nutrition.items()
            },
        })

    return weekly_plan, len(already_selected)


def _build_nutrition_report(
    db: Session,
    weekly_plan: List[dict],
    constraints: ConstraintSet,
) -> dict:
    """构建营养报告

    遍历周计划，逐道计算实际营养（调用 nutrition_service），然后汇总。
    """
    days = len(weekly_plan)
    if days == 0:
        return {
            "avg_daily_calories": 0,
            "total_calories": 0,
            "protein_g": 0, "fat_g": 0, "carbs_g": 0, "fiber_g": 0,
            "protein_pct": 0, "fat_pct": 0, "carbs_pct": 0,
            "recommendation": "暂无可用的营养数据。",
        }

    weekly_totals = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0, "fiber": 0.0}

    for day_entry in weekly_plan:
        for meal_slot in ["breakfast", "lunch", "dinner"]:
            meal = day_entry["meals"].get(meal_slot)
            if not meal:
                continue
            try:
                # A planned meal means one serving.  Use the recipe's declared
                # servings when deriving `per_serving`; forcing servings=1
                # incorrectly counted the complete recipe batch as one meal.
                servings = int(meal.get("serving_size", 1) or 1)
                nut = calculate_recipe_nutrition(db, meal["recipe_id"])
                per = nut["per_serving"]
                for key in weekly_totals:
                    weekly_totals[key] += per[key] * servings
            except Exception:
                pass

    total_cal = weekly_totals["calories"]
    avg_cal = round(total_cal / days, 0) if days > 0 else 0
    protein_cal = weekly_totals["protein"] * 4
    fat_cal = weekly_totals["fat"] * 9
    carbs_cal = weekly_totals["carbs"] * 4
    total_macro_cal = protein_cal + fat_cal + carbs_cal or 1

    protein_pct = round(protein_cal / total_macro_cal, 2)
    fat_pct = round(fat_cal / total_macro_cal, 2)
    carbs_pct = round(carbs_cal / total_macro_cal, 2)

    # 生成建议
    goal = constraints.health_goal
    if goal == "fat_loss":
        if constraints.calorie_min <= avg_cal <= constraints.calorie_max:
            rec = f"本周平均每日摄入 {avg_cal:.0f}kcal，处于减脂目标区间 ({constraints.calorie_min:.0f}-{constraints.calorie_max:.0f}kcal)。蛋白质占比 {protein_pct*100:.0f}%，有助于减脂期保留肌肉。"
        elif avg_cal < constraints.calorie_min:
            rec = f"本周平均每日摄入 {avg_cal:.0f}kcal，低于减脂目标下限 ({constraints.calorie_min:.0f}kcal)，建议增加优质主食或蛋白质，避免长期摄入不足。"
        else:
            rec = f"本周平均每日摄入 {avg_cal:.0f}kcal，略高于减脂目标 ({constraints.calorie_max:.0f}kcal)，建议适当减少主食分量。"
    elif goal == "muscle_gain":
        rec = f"本周平均每日摄入 {avg_cal:.0f}kcal，蛋白质 {weekly_totals['protein']/days:.0f}g/天，有助于肌肉合成。建议配合力量训练效果更佳。"
    elif goal == "blood_sugar":
        rec = f"本周平均每日摄入 {avg_cal:.0f}kcal，碳水占比 {carbs_pct*100:.0f}%，适合控糖饮食需求。"
    else:
        rec = f"本周平均每日摄入 {avg_cal:.0f}kcal，营养搭配均衡。蛋白质 {protein_pct*100:.0f}%、脂肪 {fat_pct*100:.0f}%、碳水 {carbs_pct*100:.0f}%。"

    return {
        "avg_daily_calories": round(avg_cal, 0),
        "total_calories": round(total_cal, 0),
        "protein_g": round(weekly_totals["protein"] / days, 0),
        "fat_g": round(weekly_totals["fat"] / days, 0),
        "carbs_g": round(weekly_totals["carbs"] / days, 0),
        "fiber_g": round(weekly_totals["fiber"] / days, 1),
        "protein_pct": protein_pct,
        "fat_pct": fat_pct,
        "carbs_pct": carbs_pct,
        "recommendation": rec,
    }


def _adjust_meal_servings(
    db: Session,
    weekly_plan: List[dict],
    constraints: ConstraintSet,
) -> None:
    """Adjust portions per meal slot without creating unrealistic meals."""
    for day in weekly_plan:
        nutrition_by_recipe = {}
        for meal in day.get("meals", {}).values():
            if not meal:
                continue
            recipe_id = meal["recipe_id"]
            if recipe_id not in nutrition_by_recipe:
                nutrition_by_recipe[recipe_id] = calculate_recipe_nutrition(
                    db, recipe_id
                )["per_serving"]

        for slot, meal in day.get("meals", {}).items():
            if not meal:
                continue
            calories = nutrition_by_recipe[meal["recipe_id"]]["calories"]
            target = constraints.target_calories * MEAL_CALORIE_RATIOS[slot]
            max_servings = MEAL_MAX_SERVINGS[slot]
            servings = int(meal.get("serving_size", 1) or 1)
            while servings < max_servings and abs(target - (servings + 1) * calories) < abs(target - servings * calories):
                servings += 1
            meal["serving_size"] = servings


def _build_shopping_list(
    db: Session,
    weekly_plan: List[dict],
    owned_ids: List[int],
) -> dict:
    """构建采购清单

    收集周计划中所有菜谱的食材，减去已有食材，按分类分组。
    """
    # Keep every meal occurrence. A set would silently discard repeats and
    # understate the quantity that needs to be bought for the week.
    recipe_occurrences: List[Tuple[int, int]] = []
    for day_entry in weekly_plan:
        for meal_slot in ["breakfast", "lunch", "dinner"]:
            meal = day_entry["meals"].get(meal_slot)
            if meal:
                recipe_occurrences.append(
                    (meal["recipe_id"], int(meal.get("serving_size", 1) or 1))
                )

    # 收集所有需要的食材
    needed: Dict[int, dict] = {}
    for rid, servings in recipe_occurrences:
        ingredients = get_recipe_ingredients(db, rid)
        for ing in ingredients:
            iid = ing["ingredient_id"]
            if iid not in needed:
                needed[iid] = {
                    "ingredient_id": iid,
                    "name": ing["name"],
                    "quantity": 0.0,
                    "unit": ing.get("purchase_unit", ing["unit"]),
                    "unit_price": ing["unit_price"],
                    "category": ing["category"],
                    "for_recipes": [],
                }
            purchase_unit = needed[iid]["unit"]
            needed[iid]["quantity"] += convert_quantity(
                quantity=ing["quantity"] * servings,
                from_unit=ing["unit"],
                to_unit=purchase_unit,
                category=ing["category"],
            )
            needed[iid]["for_recipes"].append({"recipe_id": rid, "name": ""})

    # 减去已有食材
    owned_set = set(owned_ids or [])
    to_buy = {iid: info for iid, info in needed.items() if iid not in owned_set}

    # 按分类分组
    by_category: Dict[str, list] = {}
    total_cost = 0.0
    items = []

    for iid, info in sorted(to_buy.items(), key=lambda x: x[1]["category"]):
        quantity = info["quantity"]
        if info["unit"] in DISCRETE_PURCHASE_UNITS:
            # Whole items/packages cannot be bought fractionally.
            import math
            quantity = math.ceil(quantity)
        item_cost = round(quantity * info["unit_price"], 2)
        items.append({
            "ingredient_id": iid,
            "name": info["name"],
            "quantity": round(quantity, 1),
            "unit": info["unit"],
            "estimated_cost": item_cost,
            "for_recipes": info["for_recipes"],
        })
        total_cost += item_cost

        cat_display = _category_display(info["category"])
        if cat_display not in by_category:
            by_category[cat_display] = []
        by_category[cat_display].append({
            "name": info["name"],
            "quantity": round(quantity, 1),
            "unit": info["unit"],
            "estimated_cost": item_cost,
        })

    return {
        "total_cost": round(total_cost, 2),
        "items": items,
        "by_category": by_category,
    }


def _category_display(cat: str) -> str:
    """食材分类的中文显示"""
    mapping = {
        "vegetable": "蔬菜", "meat": "肉类", "seafood": "水产",
        "dairy": "乳制品", "grain": "主食", "fruit": "水果",
        "condiment": "调料", "egg": "蛋类", "other": "其他",
    }
    return mapping.get(cat, cat)


def _build_summary(
    top5: List[dict],
    weekly_plan: List[dict],
    shopping_list: dict,
    nutrition_report: dict,
    constraints: ConstraintSet,
) -> str:
    """生成总结文案"""
    top_names = [t["name"] for t in top5[:3]]
    total_budget = constraints.total_budget
    shopping_cost = shopping_list.get("total_cost", 0)

    goal_display = {"fat_loss": "减脂", "muscle_gain": "增肌", "blood_sugar": "控糖", "healthy": "健康饮食"}
    goal_name = goal_display.get(constraints.health_goal, "饮食")
    lines = [
        f"📋 本周{goal_name}计划已为你规划完毕！\n",
        f"总预算 {total_budget} 元，预计采购花费约 {shopping_cost:.1f} 元。\n",
        f"\n本周重点推荐「{'」、「'.join(top_names)}」等菜谱，"
        "它们在营养匹配度、预算和时令方面得分非常高。\n",
        f"\n📌 采购建议：周末集中采购一次，肉类和蔬菜可以冷藏保存 3-4 天。\n",
        f"\n💪 每日平均摄入 {nutrition_report.get('avg_daily_calories', 0):.0f}kcal，"
        f"建议配合适量运动，效果更好！\n",
        f"\n🍳 所有菜谱均可在 30 分钟内完成，适合工作日晚餐。",
    ]
    return "".join(lines)


def validate_weekly_plan(
    weekly_plan: List[dict],
    nutrition_report: dict,
    ranked_recipes: List[ScoredRecipe],
    constraints: ConstraintSet,
    shopping_list: Optional[dict] = None,
) -> dict:
    """校验规划完整性与可解释的软约束偏差。

    校验不会放宽安全硬约束；热量和重复度等属于结果质量问题，以 warning 呈现。
    """
    warnings: List[str] = []
    missing_meals: List[dict] = []
    recipe_counts: Dict[int, int] = {}
    cost_by_id = {item.recipe_id: item.estimated_cost for item in ranked_recipes}
    plan_cost = 0.0

    for day in weekly_plan:
        for slot in ["breakfast", "lunch", "dinner"]:
            meal = day.get("meals", {}).get(slot)
            if not meal:
                missing_meals.append({"day": day.get("day"), "meal_slot": slot})
                continue
            recipe_id = meal["recipe_id"]
            recipe_counts[recipe_id] = recipe_counts.get(recipe_id, 0) + 1
            plan_cost += cost_by_id.get(recipe_id, 0.0) * int(meal.get("serving_size", 1) or 1)

    if missing_meals:
        warnings.append(f"有 {len(missing_meals)} 个餐次未生成，请扩充对应餐次的菜谱库。")

    avg_calories = float(nutrition_report.get("avg_daily_calories") or 0)
    # 启发式方案允许 20% 弹性，超过后明确提示而不是宣称达标。
    lower_bound = constraints.calorie_min * 0.8
    upper_bound = constraints.calorie_max * 1.2
    if avg_calories and not lower_bound <= avg_calories <= upper_bound:
        warnings.append(
            f"日均热量 {avg_calories:.0f}kcal 超出建议弹性区间 "
            f"({lower_bound:.0f}-{upper_bound:.0f}kcal)。"
        )

    procurement_cost = float((shopping_list or {}).get("total_cost", plan_cost))
    if constraints.total_budget > 0 and procurement_cost > constraints.total_budget:
        warnings.append(
            f"预计采购成本 {procurement_cost:.1f} 元超过总预算 {constraints.total_budget:.1f} 元。"
        )
    elif constraints.total_budget > 0 and procurement_cost < constraints.total_budget * BUDGET_UTILIZATION_MIN:
        warnings.append(
            f"预计采购成本 {procurement_cost:.1f} 元低于预算利用目标 "
            f"({constraints.total_budget * BUDGET_UTILIZATION_MIN:.1f}-{constraints.total_budget:.1f} 元)。"
        )

    repeated = [recipe_id for recipe_id, count in recipe_counts.items() if count > 3]
    if repeated:
        warnings.append(f"有 {len(repeated)} 道菜一周出现超过 3 次，建议后续扩充菜谱多样性。")

    return {
        "passed": not missing_meals,
        "missing_meals": missing_meals,
        "avg_daily_calories": round(avg_calories, 1),
        "target_calorie_range": [round(constraints.calorie_min, 1), round(constraints.calorie_max, 1)],
        "estimated_plan_cost": round(plan_cost, 2),
        "estimated_procurement_cost": round(procurement_cost, 2),
        "budget_target_range": [
            round(constraints.total_budget * BUDGET_UTILIZATION_MIN, 2),
            round(constraints.total_budget, 2),
        ],
        "total_budget": round(constraints.total_budget, 2),
        "max_recipe_repeats": max(recipe_counts.values(), default=0),
        "warnings": warnings,
    }


def aggregate_and_rank(
    db: Session,
    constraints: ConstraintSet,
    current_season: str = "夏季",
    owned_ingredient_ids: Optional[List[int]] = None,
    duration_days: int = 7,
    meal_count_per_day: int = 3,
    weights: Optional[Dict[str, float]] = None,
    ranked_recipes: Optional[List[ScoredRecipe]] = None,
) -> dict:
    """完整聚合：TOP5 + 周计划 + 营养报告 + 采购清单 + 总结

    Args:
        db: 数据库会话
        constraints: 约束集
        current_season: 当前季节
        owned_ingredient_ids: 用户已有食材 ID 列表
        duration_days: 规划天数
        meal_count_per_day: 每日餐数（1-3）
        weights: 评分权重

    Returns:
        完整的规划结果 dict（可直接存入 meal_plans.result_json）
    """
    w = weights or DEFAULT_WEIGHTS
    owned_ids = owned_ingredient_ids or []

    # 1. 获取排序结果（TOP15 用于周计划的候选池）
    ranked = ranked_recipes or rank_candidates(
        db, constraints, current_season, owned_ids, w, top_n=15,
    )

    # 2. 构建候选池（用于周计划的 variety 重评）
    pool = build_candidate_pool(db)
    candidate_map = {c.recipe_id: c for c in pool}

    # 3. 提取 TOP5
    top5 = _build_top5(ranked, constraints)

    # 4. 贪心生成周计划
    weekly_plan, _ = _greedy_weekly_plan(
        db, pool, ranked, constraints, current_season, owned_ids, w,
        duration_days=duration_days,
        meal_count_per_day=meal_count_per_day,
        owned_recipes_map=candidate_map,
    )

    _adjust_meal_servings(db, weekly_plan, constraints)

    # 5. 计算营养报告
    nutrition_report = _build_nutrition_report(db, weekly_plan, constraints)

    # 6. 构建采购清单
    shopping_list = _build_shopping_list(db, weekly_plan, owned_ids)

    # 7. 补充 TOP5 的营养数据
    for item in top5:
        try:
            nut = calculate_recipe_nutrition(db, item["recipe_id"])
            item["nutrition"] = {
                "calories": nut["per_serving"]["calories"],
                "protein": nut["per_serving"]["protein"],
                "fat": nut["per_serving"]["fat"],
                "carbs": nut["per_serving"]["carbs"],
                "fiber": nut["per_serving"]["fiber"],
            }
        except Exception:
            pass

    # 补充周计划每餐营养
    for day_entry in weekly_plan:
        day_totals = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        for meal_slot in ["breakfast", "lunch", "dinner"]:
            meal = day_entry["meals"].get(meal_slot)
            if meal:
                try:
                    nut = calculate_recipe_nutrition(db, meal["recipe_id"])
                    servings = int(meal.get("serving_size", 1) or 1)
                    meal["nutrition"] = {
                        key: round(value * servings, 1)
                        for key, value in nut["per_serving"].items()
                    }
                    for key in day_totals:
                        day_totals[key] += meal["nutrition"][key]
                except Exception:
                    pass
        day_entry["total_nutrition"] = {
            key: round(value, 1) for key, value in day_totals.items()
        }

    # 补充采购清单中菜谱名称
    for item in shopping_list.get("items", []):
        for ref in item.get("for_recipes", []):
            for r in top5 + [{"recipe_id": 0, "name": ""}]:
                if ref["recipe_id"] == r.get("recipe_id"):
                    ref["name"] = r.get("name", "")
                    break

    # 8. 生成总结
    summary = _build_summary(top5, weekly_plan, shopping_list, nutrition_report, constraints)
    plan_validation = validate_weekly_plan(
        weekly_plan, nutrition_report, ranked, constraints, shopping_list
    )

    return {
        "top5": top5,
        "weekly_plan": weekly_plan,
        "nutrition_report": nutrition_report,
        "shopping_list": shopping_list,
        "summary": summary,
        "plan_validation": plan_validation,
    }
