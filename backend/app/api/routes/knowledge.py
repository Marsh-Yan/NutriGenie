"""通用知识库检索接口。"""

from fastapi import APIRouter, Depends

from app.api.schemas.knowledge import (
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
)
from app.rag.vector_store import KnowledgeVectorStore
from app.services.security import get_current_user

router = APIRouter(tags=["knowledge"])


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    data: KnowledgeSearchRequest,
    _: object = Depends(get_current_user),
):
    where = {"source_type": data.source_type} if data.source_type else None
    results = KnowledgeVectorStore().hybrid_search(data.query, limit=data.limit, where=where)
    return KnowledgeSearchResponse(
        query=data.query,
        results=[
            KnowledgeSearchResult(
                chunk_id=item.chunk_id,
                content=item.content,
                source_file=item.metadata.get("source_file"),
                source_type=item.metadata.get("source_type"),
                document_id=str(item.metadata["document_id"])
                if item.metadata.get("document_id") is not None
                else None,
                page_number=item.metadata.get("page_number"),
                section_title=item.metadata.get("h2") or item.metadata.get("h1"),
                score=round(item.similarity_score, 6),
            )
            for item in results
        ],
    )
