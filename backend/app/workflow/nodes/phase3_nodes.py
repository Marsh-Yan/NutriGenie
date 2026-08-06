"""Phase 3 计算节点包装

将 Phase 3 的纯代码服务包装为 LangGraph Node 函数。
每个节点接收 WorkflowState，处理核心逻辑，返回更新后的 WorkflowState。
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.profile import Profile
from app.models.ingredient import Ingredient
from app.services.constraint_analyzer import build_constraints
from app.services.recommendation_engine import (
    rank_candidates,
    rank_candidates_hybrid,
    HYBRID_WEIGHTS,
    resolve_allergen_ingredient_ids,
)
from app.rag.recipe_retriever import retrieve_recipes
from app.services.aggregate_service import aggregate_and_rank
from app.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


def _get_db() -> Session:
    """获取数据库会话"""
    return SessionLocal()


def _resolve_owned_ids(db: Session, state: WorkflowState) -> list:
    """将用户输入的已有食材名解析为食材 ID"""
    names = state.intent_analysis.get("owned_ingredients", []) if state.intent_analysis else []
    if not names:
        return []

    all_ings = db.query(Ingredient).all()
    name_map = {ing.name: ing.ingredient_id for ing in all_ings}
    # 也支持部分匹配
    ids = []
    for name in names:
        if name in name_map:
            ids.append(name_map[name])
        else:
            # 尝试部分匹配
            for ing_name, ing_id in name_map.items():
                if name in ing_name or ing_name in name:
                    ids.append(ing_id)
                    break

    state.owned_ingredient_ids = list(set(ids))
    return state.owned_ingredient_ids


def constraint_node(state: WorkflowState) -> WorkflowState:
    """约束分析节点

    从用户画像和意图分析结果构建约束集。
    """
    state.current_node = "constraint_analyzer"

    db = _get_db()
    try:
        profile = db.query(Profile).filter(Profile.profile_id == state.profile_id).first()
        if not profile:
            state.constraint_error = f"用户画像 (id={state.profile_id}) 不存在"
            state.errors.append(state.constraint_error)
            return state

        # 如果 intent_analysis 中有自定义参数，覆盖 profile
        intent = state.intent_analysis or {}
        effective_diet = intent.get("diet_type") or profile.diet_type
        effective_goal = intent.get("health_goal") or profile.health_goal

        # 临时修改 profile 属性
        original_diet = profile.diet_type
        original_goal = profile.health_goal
        profile.diet_type = effective_diet
        profile.health_goal = effective_goal

        try:
            constraints = build_constraints(
                profile=profile,
                duration_days=state.duration_days,
                total_budget=state.total_budget,
            )
        finally:
            profile.diet_type = original_diet
            profile.health_goal = original_goal

        state.constraints = constraints.to_dict()
        logger.info(f"Constraints built: {constraints}")

    except Exception as e:
        logger.exception("Constraint analysis failed")
        state.constraint_error = str(e)
        state.errors.append(str(e))
    finally:
        db.close()

    return state


def recommendation_node(state: WorkflowState) -> WorkflowState:
    """推荐引擎节点

    召回 → 排除（过敏原）→ 评分 → 排序 → TOP15
    """
    state.current_node = "recommendation_engine"

    if not state.constraints:
        state.recommendation_error = "缺少约束集"
        state.errors.append(state.recommendation_error)
        return state

    db = _get_db()
    try:
        # 从约束重建 ConstraintSet 对象
        from app.services.constraint_analyzer import ConstraintSet

        c = state.constraints
        constraints = ConstraintSet(
            target_calories=c["target_calories"],
            calorie_min=c["calorie_min"],
            calorie_max=c["calorie_max"],
            target_protein=c["target_protein"],
            daily_budget=c["daily_budget"],
            total_budget=c["total_budget"],
            excluded_ingredient_ids=c["excluded_ingredient_ids"],
            allergen_names=c["allergen_names"],
            diet_type=c["diet_type"],
            health_goal=c["health_goal"],
            macro_split=(c["macro_split"]["protein_pct"],
                         c["macro_split"]["fat_pct"],
                         c["macro_split"]["carbs_pct"]),
            tdee=c["tdee"],
            bmr=c["bmr"],
        )

        # 解析已有食材名 → ID
        _resolve_owned_ids(db, state)

        semantic_scores = {}
        semantic_ids = []
        rag_used = False
        if state.rag_enabled:
            try:
                retrieved = retrieve_recipes(state.intent_analysis or {}, state.constraints, limit=30)
                semantic_scores = {item.recipe_id: item.similarity_score for item in retrieved}
                semantic_ids = [item.recipe_id for item in retrieved]
                rag_used = True
            except Exception as exc:
                state.rag_retrieval_error = str(exc)
                logger.warning("RAG retrieval unavailable, using deterministic fallback: %s", exc)

        # 执行混合重排；RAG 失败时语义分为空，仍保留结构化候选和硬过滤。
        ranked = rank_candidates_hybrid(
            db=db,
            constraints=constraints,
            semantic_scores=semantic_scores,
            semantic_recipe_ids=semantic_ids,
            current_season="夏季",
            owned_ingredient_ids=state.owned_ingredient_ids,
            top_n=15,
        )
        state.recommendation_meta = {
            "strategy": "hybrid_rag_v1",
            "rag_enabled": state.rag_enabled,
            "rag_used": rag_used,
            "fallback_used": state.rag_enabled and not rag_used,
            "candidate_count": len(ranked),
            "weight_version": "hybrid_v1",
        }

        state.ranked_recipes = [
            {
                "recipe_id": r.recipe_id,
                "name": r.name,
                "category": r.category,
                "cuisine_type": r.cuisine_type,
                "difficulty": r.difficulty,
                "prep_time": r.prep_time,
                "cook_time": r.cook_time,
                "servings": r.servings,
                "image_url": r.image_url,
                "total_calories": r.total_calories,
                "estimated_cost": r.estimated_cost,
                "scores": r.scores,
                "total_score": r.total_score,
                "evidence": r.evidence,
            }
            for r in ranked
        ]

        logger.info(f"Recommendations: {len(state.ranked_recipes)} recipes ranked")

    except Exception as e:
        logger.exception("Recommendation failed")
        state.recommendation_error = str(e)
        state.errors.append(str(e))
    finally:
        db.close()

    return state


def aggregate_node(state: WorkflowState) -> WorkflowState:
    """聚合节点

    TOP5 + 贪心周计划 + 营养报告 + 采购清单
    """
    state.current_node = "aggregator"

    if not state.constraints:
        state.aggregation_error = "缺少约束集"
        state.errors.append(state.aggregation_error)
        return state

    db = _get_db()
    try:
        from app.services.constraint_analyzer import ConstraintSet

        c = state.constraints
        constraints = ConstraintSet(
            target_calories=c["target_calories"],
            calorie_min=c["calorie_min"],
            calorie_max=c["calorie_max"],
            target_protein=c["target_protein"],
            daily_budget=c["daily_budget"],
            total_budget=c["total_budget"],
            excluded_ingredient_ids=c["excluded_ingredient_ids"],
            allergen_names=c["allergen_names"],
            diet_type=c["diet_type"],
            health_goal=c["health_goal"],
            macro_split=(c["macro_split"]["protein_pct"],
                         c["macro_split"]["fat_pct"],
                         c["macro_split"]["carbs_pct"]),
            tdee=c["tdee"],
            bmr=c["bmr"],
        )

        result = aggregate_and_rank(
            db=db,
            constraints=constraints,
            current_season="夏季",
            owned_ingredient_ids=state.owned_ingredient_ids,
            duration_days=state.duration_days,
            weights=HYBRID_WEIGHTS,
            ranked_recipes=_deserialize_ranked_recipes(state.ranked_recipes),
        )
        result["recommendation_meta"] = state.recommendation_meta

        state.aggregated_result = result
        logger.info("Aggregation complete")

    except Exception as e:
        logger.exception("Aggregation failed")
        state.aggregation_error = str(e)
        state.errors.append(str(e))
    finally:
        db.close()

    return state


def validation_node(state: WorkflowState) -> WorkflowState:
    """将聚合器的周计划校验结果显式写入 Workflow State。"""
    state.current_node = "plan_validation"
    if not state.aggregated_result:
        state.aggregation_error = "缺少聚合结果，无法校验计划"
        state.errors.append(state.aggregation_error)
        return state
    state.plan_validation = state.aggregated_result.get("plan_validation", {})
    return state


def _deserialize_ranked_recipes(items: list[dict]):
    """将工作流 State 中可 JSON 序列化的候选恢复为聚合器数据模型。"""
    from app.services.recommendation_engine import ScoredRecipe

    return [
        ScoredRecipe(
            recipe_id=item["recipe_id"], name=item["name"], category=item["category"],
            cuisine_type=item["cuisine_type"], difficulty=item["difficulty"],
            prep_time=item["prep_time"], cook_time=item["cook_time"], servings=item["servings"],
            image_url=item.get("image_url"), total_calories=item["total_calories"],
            estimated_cost=item["estimated_cost"], scores=item["scores"],
            total_score=item["total_score"], evidence=item.get("evidence", {}),
        )
        for item in items
    ]
