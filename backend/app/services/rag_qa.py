"""通用 RAG 问答：检索、上下文约束回答和引用整理。"""

from __future__ import annotations

import asyncio
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.rag.models import RetrievedChunk
from app.rag.vector_store import KnowledgeVectorStore
from app.workflow.llm import get_llm

logger = logging.getLogger(__name__)

QA_SYSTEM_PROMPT = """你是 NutriGenie 的知识库问答助手。
只能依据 <context> 中的资料回答，不得补充上下文之外的事实。
如果资料不足，请明确回答“知识库中没有足够信息”，不要猜测。
回答中的事实必须使用 [1]、[2] 这样的编号引用对应资料。
回答简洁、直接，优先使用中文；不要伪造来源编号。
"""


def _context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.metadata
        location = f"页码：{metadata.get('page_number')}" if metadata.get("page_number") else ""
        parts.append(
            f"[{index}] 文件：{metadata.get('source_file', '未知')} {location}\n"
            f"标题：{metadata.get('h2') or metadata.get('h1') or '未标注'}\n"
            f"内容：{chunk.content}"
        )
    return "\n\n".join(parts)


def _sources(chunks: list[RetrievedChunk]) -> list[dict]:
    result = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.metadata
        result.append(
            {
                "citation": f"[{index}]",
                "chunk_id": chunk.chunk_id,
                "document_id": str(metadata["document_id"]) if metadata.get("document_id") is not None else None,
                "source_file": metadata.get("source_file"),
                "page_number": metadata.get("page_number"),
                "section_title": metadata.get("h2") or metadata.get("h1"),
                "score": round(chunk.similarity_score, 6),
            }
        )
    return result


def _fallback_answer(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "知识库中没有找到足够信息。"
    return "根据知识库检索结果：\n" + "\n".join(
        f"[{index}] {chunk.content[:500].strip()}" for index, chunk in enumerate(chunks[:3], start=1)
    )


async def answer_question(
    query: str,
    *,
    limit: int = 6,
    source_type: str | None = None,
    vector_store: KnowledgeVectorStore | None = None,
) -> dict:
    """执行 RAG 问答；检索或 LLM 失败时返回可追踪降级结果。"""
    store = vector_store or KnowledgeVectorStore()
    where = {"source_type": source_type} if source_type else None
    chunks = await asyncio.to_thread(store.hybrid_search, query, limit, where)
    sources = _sources(chunks)
    retrieval = {
        "count": len(chunks),
        "top_score": round(chunks[0].similarity_score, 6) if chunks else 0.0,
        "fallback_used": False,
    }
    if not chunks or not settings.LLM_API_KEY:
        retrieval["fallback_used"] = True
        return {"answer": _fallback_answer(chunks), "sources": sources, "retrieval": retrieval}

    try:
        llm = get_llm(temperature=0.1)
        response = await llm.ainvoke(
            [
                SystemMessage(content=QA_SYSTEM_PROMPT),
                HumanMessage(content=f"用户问题：{query}\n\n<context>\n{_context(chunks)}\n</context>"),
            ]
        )
        content = response.content if isinstance(response.content, str) else str(response.content)
        if content.strip():
            return {"answer": content.strip(), "sources": sources, "retrieval": retrieval}
    except Exception as exc:
        logger.warning("RAG QA LLM failed, using retrieval fallback: %s", exc)
        retrieval["fallback_used"] = True
        retrieval["llm_error"] = str(exc)[:500]
    return {"answer": _fallback_answer(chunks), "sources": sources, "retrieval": retrieval}
