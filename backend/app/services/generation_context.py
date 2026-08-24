"""Optional grounding context for the AI-native planner."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def build_generation_query(
    user_input: str,
    intent: dict | None,
    constraints: dict,
    edit_message: str | None = None,
) -> str:
    intent = intent or {}
    parts = [user_input]
    if edit_message:
        parts.append(f"修改要求：{edit_message}")
    parts.append(f"饮食类型：{constraints.get('diet_type', '')}")
    parts.append(f"健康目标：{constraints.get('health_goal', '')}")
    preferences = intent.get("semantic_preferences") or {}
    for key in ("flavor", "scenarios", "free_text"):
        value = preferences.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    return "；".join(str(item) for item in parts if item)


def _format_context(chunks: list[Any]) -> str:
    sections = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.metadata or {}
        source = metadata.get("source_file") or metadata.get("section_title") or "知识库"
        sections.append(
            f"[{index}] 来源：{source}\n"
            f"主题：{metadata.get('h2') or metadata.get('h1') or metadata.get('topic') or '未标注'}\n"
            f"内容：{chunk.content}"
        )
    return "\n\n".join(sections)


async def retrieve_generation_context(
    *,
    user_input: str,
    intent: dict | None,
    constraints: dict,
    edit_message: str | None = None,
) -> dict:
    """Retrieve optional reference text without making RAG a hard dependency."""
    meta = {
        "mode": settings.RAG_MODE,
        "enabled": settings.RAG_MODE != "off",
        "used": False,
        "sources": [],
        "error": None,
    }
    if settings.RAG_MODE == "off":
        return {"text": "", "meta": meta}
    if not settings.EMBEDDING_API_KEY:
        meta["enabled"] = False
        meta["error"] = "未配置 EMBEDDING_API_KEY"
        return {"text": "", "meta": meta}

    query = build_generation_query(user_input, intent, constraints, edit_message)
    try:
        # Keep Chroma and its transitive dependencies optional for the main
        # LLM path.  RAG is loaded only when it is configured and requested.
        from app.rag.vector_store import KnowledgeVectorStore

        store = KnowledgeVectorStore()
        chunks = await asyncio.to_thread(
            store.hybrid_search,
            query,
            settings.RAG_CONTEXT_TOP_K,
        )
        meta["used"] = bool(chunks)
        meta["sources"] = [
            {
                "chunk_id": chunk.chunk_id,
                "source_file": (chunk.metadata or {}).get("source_file"),
                "section_title": (chunk.metadata or {}).get("h2") or (chunk.metadata or {}).get("h1"),
                "score": round(chunk.similarity_score, 4),
            }
            for chunk in chunks
        ]
        return {"text": _format_context(chunks), "meta": meta}
    except Exception as exc:
        logger.warning("Optional generation RAG unavailable: %s", exc)
        meta["error"] = str(exc)[:500]
        return {"text": "", "meta": meta}
