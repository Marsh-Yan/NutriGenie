"""RAG 问答请求和响应模型。"""

from typing import Any

from pydantic import BaseModel, Field


class KnowledgeAskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=6, ge=1, le=20)
    source_type: str | None = Field(default=None, pattern="^(markdown|txt|pdf)$")


class KnowledgeCitation(BaseModel):
    citation: str
    chunk_id: str
    document_id: str | None = None
    source_file: str | None = None
    page_number: int | None = None
    section_title: str | None = None
    score: float


class KnowledgeAskResponse(BaseModel):
    answer: str
    sources: list[KnowledgeCitation]
    retrieval: dict[str, Any]
