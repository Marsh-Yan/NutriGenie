"""从 Markdown 菜谱增强描述构建 Chroma 索引。

支持从 backend 目录直接执行：``python scripts/build_rag_index.py``。
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.document_loader import load_recipe_documents
from app.rag.vector_store import RecipeVectorStore


def main() -> None:
    documents = load_recipe_documents(BACKEND_DIR / "knowledge_base" / "recipes")
    count = RecipeVectorStore().rebuild(documents)
    print(f"RAG 索引构建完成：{count} 篇菜谱增强文档")


if __name__ == "__main__":
    main()
