"""由结构化意图生成语义检索查询。"""

from __future__ import annotations

from typing import Any

from app.rag.models import RetrievedRecipe
from app.rag.vector_store import RecipeVectorStore


def build_semantic_query(intent: dict[str, Any], constraints: dict[str, Any]) -> str:
    """只拼接风味、场景和可读目标，避免将数值约束交给向量距离判断。"""
    preferences = intent.get("semantic_preferences", {})
    flavor = preferences.get("flavor", [])
    scenarios = preferences.get("scenarios", [])
    free_text = preferences.get("free_text") or intent.get("additional_notes") or ""
    goal = intent.get("goal") or intent.get("health_goal") or constraints.get("health_goal") or "健康饮食"
    parts = [f"目标：{goal}"]
    if flavor:
        parts.append(f"口味：{'、'.join(flavor)}")
    if scenarios:
        parts.append(f"场景：{'、'.join(scenarios)}")
    if free_text:
        parts.append(f"补充需求：{free_text}")
    return "；".join(parts)


def retrieve_recipes(
    intent: dict[str, Any],
    constraints: dict[str, Any],
    vector_store: RecipeVectorStore | None = None,
    limit: int | None = None,
) -> list[RetrievedRecipe]:
    store = vector_store or RecipeVectorStore()
    return store.search(build_semantic_query(intent, constraints), limit=limit)
