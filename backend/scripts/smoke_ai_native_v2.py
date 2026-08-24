"""Run a real DeepSeek + database smoke test for the AI-native V2 plan flow.

This script intentionally does not mock the model, database, background task,
normalizer, validator, optimizer, aggregator, or version persistence. It leaves
the generated plan in the selected user's history so the result can be reviewed
through the frontend after the command succeeds.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.db.database import SessionLocal
from app.models.meal_plan import MealPlan
from app.models.meal_plan_run import MealPlanRun
from app.models.profile import Profile
from app.models.user import User
from app.tasks.plan_task import STEPS, _node_to_step_name, _resolve_node_step, enqueue_initial_plan


DEFAULT_REQUEST = (
    "请生成7天、每天早午晚三餐的减脂餐单，总预算350元；避免海鲜，"
    "以家常、适合工作日、做法清晰且菜品多样为主。"
)


def _select_profile(db, *, email: str | None, profile_id: int | None) -> tuple[Profile, str | None]:
    if profile_id is not None:
        profile = db.get(Profile, profile_id)
        if not profile:
            raise RuntimeError(f"profile_id={profile_id} 不存在")
        user = db.get(User, profile.user_id) if profile.user_id else None
        return profile, user.email if user else None

    if email:
        row = (
            db.query(Profile, User)
            .join(User, User.user_id == Profile.user_id)
            .filter(User.email == email, User.is_active.is_(True))
            .order_by(Profile.profile_id.asc())
            .first()
        )
        if not row:
            raise RuntimeError(f"找不到可用画像：{email}")
        return row[0], row[1].email

    row = (
        db.query(Profile, User)
        .join(User, User.user_id == Profile.user_id)
        .filter(User.is_active.is_(True))
        .order_by(Profile.profile_id.asc())
        .first()
    )
    if not row:
        raise RuntimeError("数据库中没有绑定有效用户的画像，请先注册并完善画像")
    return row[0], row[1].email


def _create_synthetic_profile(db) -> Profile:
    profile = Profile(
        user_id=None,
        age=30,
        gender="male",
        height=175,
        weight=70,
        activity_level="moderate",
        diet_type="balanced",
        health_goal="healthy",
        allergies=[],
        daily_budget=50,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _cleanup_synthetic(*, profile_id: int, plan_id: int) -> None:
    """Remove only the exact temporary records created by this smoke run."""
    db = SessionLocal()
    try:
        plan = db.get(MealPlan, plan_id)
        if plan:
            db.delete(plan)
            db.flush()
        profile = db.get(Profile, profile_id)
        if profile and profile.user_id is None:
            db.delete(profile)
        db.commit()
    finally:
        db.close()


def _assert_result(result: dict, *, duration_days: int) -> dict:
    meta = result.get("generation_meta") or {}
    weekly_plan = result.get("weekly_plan") or []
    recipes = result.get("recipes") or []
    meals = [meal for day in weekly_plan for meal in (day.get("meals") or {}).values()]
    ingredients = [item for recipe in recipes for item in (recipe.get("ingredients") or [])]

    checks = {
        "schema_version": result.get("schema_version") == "ai_native_v2",
        "seven_days": len(weekly_plan) == duration_days,
        "three_meals_per_day": len(meals) == duration_days * 3,
        "validation_passed": bool((result.get("validation") or {}).get("passed")),
        "ai_generated_recipes": bool(recipes)
        and all(recipe.get("source") == "ai_generated" for recipe in recipes),
        "catalog_backed_ingredients": bool(ingredients)
        and all(item.get("data_source") == "ingredient_catalog_v1" for item in ingredients),
        "no_unresolved_ingredients": not meta.get("unresolved_ingredients"),
        "minimum_diversity": int(meta.get("unique_recipe_count") or 0) >= 14,
        "repeat_limit": int(meta.get("max_recipe_repeat") or 0) <= 2,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"验收断言失败：{', '.join(failed)}")
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="真实 DeepSeek + MySQL AI-native V2 冒烟测试")
    parser.add_argument("--email", help="显式选择真实账号画像；必须同时传 --allow-account-profile")
    parser.add_argument("--profile-id", type=int, help="直接指定画像 ID，优先于 --email")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="使用不含真实账号数据的临时画像；未指定账号或画像时默认启用",
    )
    parser.add_argument(
        "--allow-account-profile",
        action="store_true",
        help="确认允许将 --email/--profile-id 对应画像发送给外部模型并保留结果",
    )
    parser.add_argument("--request", default=DEFAULT_REQUEST, help="用于真实生成的自然语言需求")
    parser.add_argument("--budget", type=float, default=350.0, help="计划总预算")
    parser.add_argument("--timeout", type=int, default=360, help="等待后台任务的最大秒数")
    args = parser.parse_args()

    if not settings.LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY 未配置；本脚本拒绝降级为 mock 或数据库菜谱")
    if (args.email or args.profile_id is not None) and not args.allow_account_profile:
        raise RuntimeError("真实账号画像需要显式传入 --allow-account-profile；建议使用默认合成画像")
    use_synthetic = args.synthetic or (not args.email and args.profile_id is None)

    db = SessionLocal()
    try:
        if use_synthetic:
            profile = _create_synthetic_profile(db)
            selected_email = None
        else:
            profile, selected_email = _select_profile(db, email=args.email, profile_id=args.profile_id)
        selected_profile_id = profile.profile_id
        plan = MealPlan(
            profile_id=profile.profile_id,
            user_input=args.request,
            duration_days=7,
            total_budget=args.budget,
            status="pending",
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        run = enqueue_initial_plan(db, plan)
        plan_id, run_id = plan.plan_id, run.run_id
    finally:
        db.close()

    print(json.dumps({
        "event": "started",
        "plan_id": plan_id,
        "run_id": run_id,
        "profile_id": selected_profile_id,
        "email": selected_email,
        "synthetic_profile": use_synthetic,
        "model": settings.PLAN_GENERATION_MODEL or settings.LLM_MODEL,
        "prompt_version": settings.PLAN_PROMPT_VERSION,
    }, ensure_ascii=False))

    started = time.monotonic()
    last_marker: tuple[str | None, str] | None = None
    final_plan = None
    final_run = None
    while time.monotonic() - started < args.timeout:
        db = SessionLocal()
        try:
            current_plan = db.get(MealPlan, plan_id)
            current_run = db.get(MealPlanRun, run_id)
            if not current_plan or not current_run:
                raise RuntimeError("实测计划或运行记录意外丢失")
            marker = (current_run.current_node, current_run.status)
            if marker != last_marker:
                order = _resolve_node_step(current_run.current_node or "")
                print(json.dumps({
                    "event": "progress",
                    "status": current_run.status,
                    "node": current_run.current_node,
                    "step": order,
                    "total_steps": len(STEPS),
                    "step_name": _node_to_step_name(current_run.current_node or ""),
                    "elapsed_seconds": round(time.monotonic() - started, 1),
                }, ensure_ascii=False))
                last_marker = marker
            if current_run.status in {"completed", "failed"}:
                final_plan = current_plan
                final_run = current_run
                if current_run.status == "completed":
                    # Detach JSON-backed fields before closing the session.
                    result = dict(current_plan.result_json or {})
                    output_version_id = current_run.output_version_id
                    repair_attempts = current_run.repair_attempts
                else:
                    error = current_run.error_message or current_plan.error_message or "未知错误"
                break
        finally:
            db.close()
        time.sleep(1)
    else:
        if use_synthetic:
            _cleanup_synthetic(profile_id=selected_profile_id, plan_id=plan_id)
        raise TimeoutError(f"真实生成超过 {args.timeout} 秒，plan_id={plan_id}, run_id={run_id}")

    elapsed = round(time.monotonic() - started, 1)
    if not final_run or final_run.status != "completed":
        if use_synthetic:
            _cleanup_synthetic(profile_id=selected_profile_id, plan_id=plan_id)
        raise RuntimeError(f"真实生成失败：{error}")

    try:
        checks = _assert_result(result, duration_days=7)
        meta = result.get("generation_meta") or {}
        report = result.get("nutrition_report") or {}
        shopping = result.get("shopping_list") or {}
        summary = {
            "event": "passed",
            "plan_id": plan_id,
            "run_id": run_id,
            "version_id": output_version_id,
            "elapsed_seconds": elapsed,
            "candidate_count": meta.get("candidate_count"),
            "unique_recipe_count": meta.get("unique_recipe_count"),
            "max_recipe_repeat": meta.get("max_recipe_repeat"),
            "repair_attempts": repair_attempts,
            "avg_daily_calories": report.get("avg_daily_calories"),
            "shopping_total_cost": shopping.get("total_cost"),
            "rag_used": meta.get("rag_used"),
            "checks": checks,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        if use_synthetic:
            _cleanup_synthetic(profile_id=selected_profile_id, plan_id=plan_id)
            print(json.dumps({
                "event": "cleanup",
                "plan_id": plan_id,
                "profile_id": selected_profile_id,
                "temporary_records_removed": True,
            }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
