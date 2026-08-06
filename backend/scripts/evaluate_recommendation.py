"""运行 Baseline 与 Hybrid RAG 推荐的离线对照评测。

需要本地 MySQL 已导入种子数据；默认结果写入被 gitignore 的
evaluation/reports/，使简历指标可以由同一命令复现。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal
from app.models.profile import Profile
from app.rag.embeddings import ZhipuEmbeddingFunction
from app.rag.recipe_retriever import build_semantic_query
from app.rag.vector_store import RecipeVectorStore
from app.services.constraint_analyzer import build_constraints
from app.services.recommendation_engine import rank_candidates, rank_candidates_hybrid


def _allergies_from_query(query: str) -> list[str]:
    mapping = {"海鲜过敏": "海鲜", "鸡蛋过敏": "鸡蛋", "花生过敏": "花生", "牛奶过敏": "牛奶"}
    return [value for keyword, value in mapping.items() if keyword in query]


def _metrics(rows: list[dict], key: str) -> dict:
    top_k = 5
    hits = sum(bool(set(row[key]) & set(row["expected_recipe_ids"])) for row in rows)
    relevant = sum(len(set(row[key]) & set(row["expected_recipe_ids"])) for row in rows)
    violations = sum(len(set(row[key]) & set(row["forbidden_recipe_ids"])) for row in rows)
    return {
        "case_count": len(rows),
        "hit_rate_at_5": round(hits / len(rows), 4) if rows else 0,
        "precision_at_5": round(relevant / (len(rows) * top_k), 4) if rows else 0,
        "hard_constraint_violations": violations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="仅评测前 N 条用例，0 表示全部")
    parser.add_argument("--offline", action="store_true", help="跳过远程 RAG 调用，验证 Baseline 路径")
    args = parser.parse_args()

    cases = json.loads((BACKEND_DIR / "evaluation" / "cases.json").read_text(encoding="utf-8"))
    if args.limit:
        cases = cases[:args.limit]

    semantic_results: list[list] = [[] for _ in cases]
    if not args.offline:
        queries = [
            build_semantic_query(
                {"health_goal": case["goal"], "semantic_preferences": {"free_text": case["query"]}},
                {"health_goal": case["goal"]},
            )
            for case in cases
        ]
        embeddings = ZhipuEmbeddingFunction().embed_documents(queries)
        semantic_results = RecipeVectorStore().search_by_embeddings(embeddings, limit=30)

    db = SessionLocal()
    rows: list[dict] = []
    try:
        for case, retrieved in zip(cases, semantic_results):
            profile = Profile(
                age=28, gender="male", height=175, weight=72,
                diet_type=case["diet_type"], health_goal=case["goal"],
                allergies=_allergies_from_query(case["query"]), daily_budget=case["budget"] / 7,
            )
            constraints = build_constraints(profile, duration_days=7, total_budget=case["budget"])
            baseline = rank_candidates(db, constraints, top_n=5)
            semantic_scores: dict[int, float] = {}
            semantic_ids: list[int] = []
            rag_error = None
            if not args.offline:
                semantic_scores = {item.recipe_id: item.similarity_score for item in retrieved}
                semantic_ids = list(semantic_scores)
            hybrid = rank_candidates_hybrid(
                db, constraints, semantic_scores=semantic_scores,
                semantic_recipe_ids=semantic_ids, top_n=5,
            )
            rows.append({
                **case,
                "baseline_top5": [item.recipe_id for item in baseline],
                "hybrid_top5": [item.recipe_id for item in hybrid],
                "rag_error": rag_error,
            })
    finally:
        db.close()

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "offline" if args.offline else "hybrid_rag",
        "baseline": _metrics(rows, "baseline_top5"),
        "hybrid": _metrics(rows, "hybrid_top5"),
        "cases": rows,
    }
    reports_dir = BACKEND_DIR / "evaluation" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "recommendation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    lines = ["# NutriGenie 推荐评测报告", "", f"生成时间：{report['generated_at']}", "", "| 指标 | Baseline | Hybrid RAG |", "|---|---:|---:|"]
    for metric, label in [("hit_rate_at_5", "HitRate@5"), ("precision_at_5", "Precision@5"), ("hard_constraint_violations", "硬约束违规数")]:
        lines.append(f"| {label} | {report['baseline'][metric]} | {report['hybrid'][metric]} |")
    (reports_dir / "recommendation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("评测完成：", reports_dir / "recommendation_report.md")
    print(json.dumps({"baseline": report["baseline"], "hybrid": report["hybrid"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
