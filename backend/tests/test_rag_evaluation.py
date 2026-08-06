from app.rag.evaluation import evaluate_citations, evaluate_retrieval
import json
from pathlib import Path
from app.rag.models import RetrievedChunk


def test_evaluate_retrieval_calculates_hit_recall_and_mrr():
    chunks = {
        "问题一": [RetrievedChunk("a", "", {}, 0.9), RetrievedChunk("b", "", {}, 0.8)],
        "问题二": [RetrievedChunk("x", "", {}, 0.9)],
    }
    cases = [
        {"id": "1", "query": "问题一", "relevant_chunk_ids": ["b"]},
        {"id": "2", "query": "问题二", "relevant_chunk_ids": ["missing"]},
    ]

    result = evaluate_retrieval(cases, lambda query, k: chunks[query], k=2)

    assert result["hit_rate"] == 0.5
    assert result["recall_at_k"] == 0.5
    assert result["mrr"] == 0.25
    assert result["ndcg_at_k"] > 0


def test_evaluate_retrieval_supports_graded_relevance():
    case = [{"query": "q", "relevant_grades": {"best": 3, "okay": 1}}]
    result = evaluate_retrieval(
        case,
        lambda query, k: [RetrievedChunk("okay", "", {}, 0.8), RetrievedChunk("best", "", {}, 0.7)],
        k=2,
    )

    assert 0 < result["ndcg_at_k"] < 1


def test_evaluate_citations_checks_validity_and_recall():
    result = evaluate_citations(
        "鸡蛋适合早餐 [1]，但这句话没有来源 [3]。",
        [{"citation": "[1]", "chunk_id": "breakfast-1"}, {"citation": "[2]", "chunk_id": "other-1"}],
        {"breakfast-1"},
    )

    assert result["citation_count"] == 2
    assert result["valid_citation_count"] == 1
    assert result["invalid_citation_count"] == 1
    assert result["citation_precision"] == 0.5
    assert result["citation_recall"] == 1.0


def test_evaluate_retrieval_supports_source_file_labels():
    cases = [{"query": "q", "relevant_source_files": {"guide.md": 1}}]
    result = evaluate_retrieval(
        cases,
        lambda query, k: [RetrievedChunk("chunk-1", "", {"source_file": "guide.md"}, 0.8)],
        k=1,
    )

    assert result["hit_rate"] == 1.0
    assert result["recall_at_k"] == 1.0


def test_real_eval_cases_reference_existing_recipe_documents():
    cases = json.loads(
        (Path(__file__).resolve().parents[1] / "evaluation" / "rag_eval.json").read_text(encoding="utf-8")
    )
    recipe_dir = Path(__file__).resolve().parents[1] / "knowledge_base" / "recipes"
    available = {path.name for path in recipe_dir.glob("*.md")}

    assert len(cases) == 30
    assert all(set(case["relevant_source_files"]) <= available for case in cases)
