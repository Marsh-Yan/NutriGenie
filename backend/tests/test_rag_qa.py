import pytest

from app.rag.models import RetrievedChunk
from app.services.rag_qa import answer_question


class FakeKnowledgeStore:
    def search(self, query, limit=8, where=None):
        assert query == "早餐怎么选"
        return [
            RetrievedChunk(
                chunk_id="document-1-v1-chunk-0",
                content="早餐可以选择鸡蛋和牛奶。",
                metadata={
                    "document_id": "1",
                    "source_file": "guide.md",
                    "source_type": "markdown",
                    "h2": "早餐建议",
                },
                similarity_score=0.9,
            )
        ]

    hybrid_search = search


@pytest.mark.asyncio
async def test_answer_question_returns_citations_without_llm():
    result = await answer_question("早餐怎么选", vector_store=FakeKnowledgeStore())

    assert "鸡蛋和牛奶" in result["answer"]
    assert result["sources"][0]["citation"] == "[1]"
    assert result["sources"][0]["source_file"] == "guide.md"
    assert result["retrieval"]["fallback_used"] is True


@pytest.mark.asyncio
async def test_answer_question_reports_empty_knowledge_base():
    class EmptyStore:
        def search(self, query, limit=8, where=None):
            return []

        hybrid_search = search

    result = await answer_question("不存在的问题", vector_store=EmptyStore())

    assert result["answer"] == "知识库中没有找到足够信息。"
    assert result["sources"] == []
