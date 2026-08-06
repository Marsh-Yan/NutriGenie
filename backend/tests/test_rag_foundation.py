"""RAG 基础设施测试，不调用真实智谱 API。"""

from pathlib import Path

import pytest

from app.rag.document_loader import load_recipe_documents
from app.rag.embeddings import EmbeddingError, ZhipuEmbeddingFunction
from app.rag.models import KnowledgeDocument
from app.rag.parsing.models import KnowledgeChunk
from app.rag.recipe_retriever import build_semantic_query
from app.rag.vector_store import KnowledgeVectorStore, RecipeVectorStore


class FakeEmbeddingFunction:
    """使用关键词构造确定性向量，避免测试依赖网络。"""

    def __call__(self, input):
        return self.embed_documents(list(input))

    def embed_query(self, input):
        return self.embed_documents(list(input))

    @staticmethod
    def name():
        return "fake-embedding"

    @staticmethod
    def build_from_config(config):
        return FakeEmbeddingFunction()

    def get_config(self):
        return {}

    def is_legacy(self):
        return False

    def default_space(self):
        return "cosine"

    def supported_spaces(self):
        return ["cosine", "l2", "ip"]

    def embed_documents(self, texts):
        return [self._embed(text) for text in texts]

    def _embed(self, text):
        return [
            float("暖胃" in text or "热食" in text),
            float("快手" in text or "工作日" in text),
            float("清淡" in text or "低脂" in text),
        ]


def test_load_recipe_documents_reads_generated_knowledge_base():
    recipes_dir = Path(__file__).resolve().parents[1] / "knowledge_base" / "recipes"
    documents = load_recipe_documents(recipes_dir)

    assert len(documents) >= 30
    assert documents[0].document_id == "recipe-1"
    assert documents[0].metadata["recipe_id"] == 1
    assert documents[0].metadata["document_type"] == "recipe_context"
    assert len(documents[0].metadata["content_hash"]) == 64


def test_vector_store_rebuilds_and_searches(tmp_path):
    store = RecipeVectorStore(tmp_path / "chroma", embedding_function=FakeEmbeddingFunction())
    documents = [
        KnowledgeDocument("recipe-1", "暖胃 热食 家常", {"recipe_id": 1}),
        KnowledgeDocument("recipe-2", "快手 工作日 轻食", {"recipe_id": 2}),
    ]

    assert store.rebuild(documents) == 2
    results = store.search("想吃暖胃的热食", limit=2)

    assert [item.recipe_id for item in results][0] == 1
    assert 0 <= results[0].similarity_score <= 1


def test_generic_knowledge_store_upserts_searches_and_filters(tmp_path):
    store = KnowledgeVectorStore(tmp_path / "knowledge", embedding_function=FakeEmbeddingFunction())
    chunks = [
        KnowledgeChunk(
            "document-1-v1-chunk-0",
            "暖胃 热食 家常",
            {"document_id": "1", "source_file": "guide.md", "source_type": "markdown"},
        ),
        KnowledgeChunk(
            "document-2-v1-chunk-0",
            "快手 工作日 轻食",
            {"document_id": "2", "source_file": "notes.txt", "source_type": "txt"},
        ),
    ]

    assert store.upsert(chunks) == 2
    results = store.search("暖胃热食", limit=5, where={"source_type": "markdown"})

    assert len(results) == 1
    assert results[0].chunk_id == "document-1-v1-chunk-0"
    assert results[0].metadata["source_file"] == "guide.md"


def test_generic_knowledge_store_hybrid_search_prefers_keyword_match(tmp_path):
    store = KnowledgeVectorStore(tmp_path / "hybrid", embedding_function=FakeEmbeddingFunction())
    store.upsert([
        KnowledgeChunk("a", "暖胃 热食 家常", {"source_type": "markdown", "content_hash": "a"}),
        KnowledgeChunk("b", "清淡 低脂 沙拉", {"source_type": "markdown", "content_hash": "b"}),
    ])

    results = store.hybrid_search("暖胃热食", limit=2)

    assert results[0].chunk_id == "a"
    assert "keyword_score" in results[0].metadata


def test_semantic_query_excludes_numeric_constraints():
    query = build_semantic_query(
        {
            "goal": "fat_loss",
            "semantic_preferences": {
                "flavor": ["暖胃", "清淡"],
                "scenarios": ["工作日晚餐"],
                "free_text": "不想吃水煮菜",
            },
        },
        {"daily_budget": 42.9},
    )

    assert "暖胃" in query
    assert "工作日晚餐" in query
    assert "不想吃水煮菜" in query
    assert "42.9" not in query


def test_zhipu_embedding_requires_api_key():
    embedding = ZhipuEmbeddingFunction(api_key="")
    with pytest.raises(EmbeddingError, match="EMBEDDING_API_KEY"):
        embedding.embed_documents(["测试文本"])
