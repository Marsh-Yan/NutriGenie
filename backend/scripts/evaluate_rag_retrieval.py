"""运行通用 RAG 向量/混合检索离线评测。

评测可以使用稳定的 source_file 标注，也可以使用精确的 chunk ID 标注。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.evaluation import evaluate_retrieval
from app.rag.vector_store import KnowledgeVectorStore


def main() -> None:
    cases = json.loads((BACKEND_DIR / "evaluation" / "rag_eval.json").read_text(encoding="utf-8"))
    store = KnowledgeVectorStore()
    vector = evaluate_retrieval(cases, lambda query, k: store.search(query, limit=k), k=5)
    hybrid = evaluate_retrieval(cases, lambda query, k: store.hybrid_search(query, limit=k), k=5)
    print(json.dumps({"vector": vector, "hybrid": hybrid}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
