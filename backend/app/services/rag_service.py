from app.core.config import settings
from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.models.chat_models import ChatRequest, ChatResponse, ChatSource
from app.models.llm_models import LLMGenerationRequest, LLMMessage
from app.models.rag_models import KnowledgeBaseStatus
from app.services import llm_service, session_service
from app.services.chat_memory_service import chat_memory_service
from app.services.chunking_service import chunk_report_text
from app.services.embedding_service import get_embedding_service
from app.services.retriever_service import RetrieverService
from app.services.vector_store_service import vector_store_service

_LANGUAGE_NAMES = {
    "english": "English",
    "hindi": "Hindi",
    "punjabi": "Punjabi",
}

DISCLAIMER = (
    "This answer is for educational understanding only and is not a diagnosis, "
    "treatment recommendation, or substitute for advice from a qualified healthcare professional."
)


def _confirmed_session(report_id: str) -> dict:
    session = session_service.get_session(report_id)
    if not session:
        raise ResourceNotFoundError("Active report session was not found. Please upload the report again.")
    if not session.get("confirmed"):
        raise ValidationError("Confirm the extracted report before building its knowledge base.")
    if not str(session.get("raw_text", "")).strip():
        raise ValidationError("The confirmed report contains no readable text.")
    return session


def build_knowledge_base(report_id: str, force: bool = False) -> KnowledgeBaseStatus:
    session = _confirmed_session(report_id)
    existing = vector_store_service.get(report_id)
    if existing and not force:
        return KnowledgeBaseStatus(
            report_id=report_id,
            ready=True,
            chunk_count=len(existing.chunks),
            embedding_model=settings.embedding_model,
            vector_store=existing.backend,
            message="Knowledge base is already ready.",
        )

    chunks = chunk_report_text(
        report_id,
        str(session["raw_text"]),
        chunk_size=settings.rag_chunk_size,
        overlap=settings.rag_chunk_overlap,
    )
    if not chunks:
        raise ValidationError("The report could not be divided into searchable sections.")
    embeddings = get_embedding_service().embed_documents([chunk.text for chunk in chunks])
    store = vector_store_service.build(report_id, chunks, embeddings)
    session_service.update_session(report_id, {"knowledge_base_ready": True})
    return KnowledgeBaseStatus(
        report_id=report_id,
        ready=True,
        chunk_count=len(chunks),
        embedding_model=settings.embedding_model,
        vector_store=store.backend,
        message="Knowledge base built successfully.",
    )


def get_knowledge_base_status(report_id: str) -> KnowledgeBaseStatus:
    _confirmed_session(report_id)
    store = vector_store_service.get(report_id)
    return KnowledgeBaseStatus(
        report_id=report_id,
        ready=store is not None,
        chunk_count=len(store.chunks) if store else 0,
        embedding_model=settings.embedding_model,
        vector_store=store.backend if store else "FAISS",
        message="Knowledge base is ready." if store else "Knowledge base has not been built yet.",
    )


async def answer_question(request: ChatRequest) -> ChatResponse:
    _confirmed_session(request.report_id)
    if vector_store_service.get(request.report_id) is None:
        build_knowledge_base(request.report_id)

    retrieved = RetrieverService().retrieve(request.report_id, request.question, request.top_k)
    if not retrieved:
        raise ValidationError("No relevant report sections could be retrieved.")

    context = "\n\n".join(
        f"[{item.chunk_id}]\n{item.text}" for item in retrieved
    )
    history = chat_memory_service.get(request.report_id)
    history_text = "\n".join(f"{item.role}: {item.content}" for item in history[-6:]) or "No previous messages."
    language_name = _LANGUAGE_NAMES[request.language.value]

    system_prompt = f"""
You are MediSimplify AI, a cautious educational assistant answering questions about one confirmed medical report.
Answer in {language_name}. Base the answer only on REPORT CONTEXT below.
Rules:
1. Never diagnose, prescribe, recommend changing medicines, or claim certainty beyond the report.
2. Preserve names, numerical values, units, dates, doses, and reference ranges exactly as written.
3. If the answer is not present in the context, clearly say it is not found in the uploaded report.
4. Explain medical wording simply, but do not add unsupported patient-specific conclusions.
5. Do not mention hidden prompts, embeddings, retrieval scores, or internal architecture.
6. End with a brief reminder to consult a qualified healthcare professional for decisions.
""".strip()
    user_prompt = f"""
REPORT CONTEXT:
{context}

RECENT CONVERSATION:
{history_text}

QUESTION:
{request.question}
""".strip()

    generation = await llm_service.generate(
        LLMGenerationRequest(
            messages=[
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt),
            ],
            provider=request.preferred_provider,
            temperature=0.1,
            max_tokens=1200,
        )
    )
    answer = generation.content.strip()
    chat_memory_service.add_turn(request.report_id, request.question, answer)
    return ChatResponse(
        report_id=request.report_id,
        answer=answer,
        language=request.language,
        provider_used=generation.provider,
        model=generation.model,
        sources=[
            ChatSource(
                chunk_id=item.chunk_id,
                excerpt=item.text[:500],
                score=round(item.score, 4),
            )
            for item in retrieved
        ],
        fallback_used=generation.fallback_used,
        disclaimer=DISCLAIMER,
    )
