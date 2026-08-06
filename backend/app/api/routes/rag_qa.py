"""带引用的通用 RAG 问答接口。"""

from fastapi import APIRouter, Depends

from app.api.schemas.rag_qa import KnowledgeAskRequest, KnowledgeAskResponse
from app.services.rag_qa import answer_question
from app.services.security import get_current_user

router = APIRouter(tags=["knowledge"])


@router.post("/knowledge/ask", response_model=KnowledgeAskResponse)
async def ask_knowledge(
    data: KnowledgeAskRequest,
    _: object = Depends(get_current_user),
):
    return await answer_question(
        data.query,
        limit=data.limit,
        source_type=data.source_type,
    )
