"""通用知识库检索 API 模型。"""

from pydantic import BaseModel, Field


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=8, ge=1, le=50)
    source_type: str | None = Field(default=None, pattern="^(markdown|txt|pdf)$")


class KnowledgeSearchResult(BaseModel):
    chunk_id: str
    content: str
    source_file: str | None = None
    source_type: str | None = None
    document_id: str | None = None
    page_number: int | None = None
    section_title: str | None = None
    score: float


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeSearchResult]
