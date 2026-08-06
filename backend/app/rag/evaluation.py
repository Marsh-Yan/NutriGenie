"""RAG 检索离线评测指标与运行器。"""

from __future__ import annotations

from collections.abc import Callable, Iterable
import math
import re
from typing import Any

from app.rag.models import RetrievedChunk


def _metrics(results: list[list[str]], expected: list[dict[str, float]], k: int) -> dict[str, float]:
    hits = []
    reciprocal_ranks = []
    recalls = []
    ndcgs = []
    for ids, relevant in zip(results, expected):
        top = ids[:k]
        positions = [index + 1 for index, item in enumerate(top) if item in relevant]
        hits.append(bool(positions))
        reciprocal_ranks.append(1.0 / min(positions) if positions else 0.0)
        recalls.append(len(set(top) & set(relevant)) / max(1, len(relevant)))
        dcg = sum(
            (2 ** relevant.get(item, 0) - 1) / math.log2(index + 2)
            for index, item in enumerate(top)
        )
        ideal = sorted(relevant.values(), reverse=True)[:k]
        idcg = sum((2 ** grade - 1) / math.log2(index + 2) for index, grade in enumerate(ideal))
        ndcgs.append(dcg / idcg if idcg else 0.0)
    count = max(1, len(expected))
    return {
        "hit_rate": sum(hits) / count,
        "recall_at_k": sum(recalls) / count,
        "mrr": sum(reciprocal_ranks) / count,
        "ndcg_at_k": sum(ndcgs) / count,
    }


def evaluate_retrieval(
    cases: Iterable[dict[str, Any]],
    retriever: Callable[[str, int], list[RetrievedChunk]],
    *,
    k: int = 5,
) -> dict[str, Any]:
    """对给定检索器评估命中率、Recall@K 和 MRR。"""
    cases = list(cases)
    retrieved_ids: list[list[str]] = []
    expected_ids: list[dict[str, float]] = []
    details = []
    for case in cases:
        chunks = retriever(case["query"], k)
        ids = [chunk.chunk_id for chunk in chunks]
        if case.get("relevant_source_files"):
            relevant = {str(name): float(grade) for name, grade in case["relevant_source_files"].items()}
            metric_ids = [str(chunk.metadata.get("source_file")) for chunk in chunks]
        else:
            relevant = {
                str(chunk_id): float(grade)
                for chunk_id, grade in (
                    case.get("relevant_grades")
                    or {chunk_id: 1 for chunk_id in case.get("relevant_chunk_ids", [])}
                ).items()
            }
            metric_ids = ids
        retrieved_ids.append(metric_ids)
        expected_ids.append(relevant)
        details.append({"id": case.get("id"), "retrieved": ids, "relevant": relevant})
    return {"k": k, "count": len(cases), **_metrics(retrieved_ids, expected_ids, k), "details": details}


def evaluate_citations(
    answer: str,
    sources: list[dict[str, Any]],
    expected_source_ids: set[str] | None = None,
) -> dict[str, Any]:
    """评估答案中的 [n] 引用是否存在且指向相关来源。"""
    references = re.findall(r"\[(\d+)\]", answer or "")
    cited_numbers = {int(number) for number in references}
    source_by_number = {index + 1: source for index, source in enumerate(sources)}
    valid_numbers = cited_numbers & set(source_by_number)
    cited_ids = {
        str(source_by_number[number].get("chunk_id"))
        for number in valid_numbers
        if source_by_number[number].get("chunk_id") is not None
    }
    expected = {str(item) for item in (expected_source_ids or set())}
    relevant_cited = cited_ids & expected
    return {
        "citation_count": len(cited_numbers),
        "valid_citation_count": len(valid_numbers),
        "invalid_citation_count": len(cited_numbers - valid_numbers),
        "citation_precision": len(valid_numbers) / max(1, len(cited_numbers)),
        "citation_recall": len(relevant_cited) / max(1, len(expected)),
        "cited_chunk_ids": sorted(cited_ids),
    }
