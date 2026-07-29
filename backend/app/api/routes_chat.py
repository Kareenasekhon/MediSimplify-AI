from fastapi import APIRouter, status

from app.models.chat_models import (
    ChatRequest,
    ChatResponse,
    ClearConversationResponse,
    SuggestedQuestionsResponse,
)
from app.models.rag_models import KnowledgeBaseStatus
from app.services import rag_service
from app.services.chat_memory_service import chat_memory_service
from app.services.vector_store_service import vector_store_service

router = APIRouter(prefix="/chat", tags=["Intelligent Medical Assistant"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_with_report(request: ChatRequest) -> ChatResponse:
    return await rag_service.answer_question(request)


@router.get(
    "/{report_id}/suggested-questions",
    response_model=SuggestedQuestionsResponse,
    status_code=status.HTTP_200_OK,
)
async def suggested_questions(report_id: str) -> SuggestedQuestionsResponse:
    return rag_service.get_suggested_questions(report_id)


@router.post(
    "/{report_id}/knowledge-base",
    response_model=KnowledgeBaseStatus,
    status_code=status.HTTP_200_OK,
)
async def build_knowledge_base(report_id: str, force: bool = False) -> KnowledgeBaseStatus:
    return rag_service.build_knowledge_base(report_id, force=force)


@router.get(
    "/{report_id}/status",
    response_model=KnowledgeBaseStatus,
    status_code=status.HTTP_200_OK,
)
async def knowledge_base_status(report_id: str) -> KnowledgeBaseStatus:
    return rag_service.get_knowledge_base_status(report_id)


@router.delete(
    "/{report_id}/conversation",
    response_model=ClearConversationResponse,
    status_code=status.HTTP_200_OK,
)
async def clear_conversation(report_id: str) -> ClearConversationResponse:
    cleared = chat_memory_service.clear(report_id)
    return ClearConversationResponse(
        report_id=report_id,
        cleared=cleared,
        message="Conversation cleared." if cleared else "Conversation was already empty.",
    )


@router.delete(
    "/{report_id}/knowledge-base",
    response_model=KnowledgeBaseStatus,
    status_code=status.HTTP_200_OK,
)
async def delete_knowledge_base(report_id: str) -> KnowledgeBaseStatus:
    vector_store_service.delete(report_id)
    chat_memory_service.clear(report_id)
    return rag_service.get_knowledge_base_status(report_id)
