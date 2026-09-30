import logging
import time

from app.core.config import settings
from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.models.chat_models import (
    ChatMode,
    ChatRequest,
    ChatResponse,
    ChatSource,
    ExplanationStyle,
    SuggestedQuestionsResponse,
)
from app.models.llm_models import LLMGenerationRequest, LLMMessage
from app.models.rag_models import KnowledgeBaseStatus
from app.services import llm_service, session_service
from app.services.chat_memory_service import chat_memory_service
from app.services.chunking_service import chunk_report_text
from app.services.embedding_service import get_embedding_service
from app.services.question_router_service import classify_question
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
        raise ResourceNotFoundError(
            "Active report session was not found. Please upload the report again."
        )

    if not session.get("confirmed"):
        raise ValidationError(
            "Confirm the extracted report before building its knowledge base."
        )

    if not str(session.get("raw_text", "")).strip():
        raise ValidationError(
            "The confirmed report contains no readable text."
        )

    return session


def build_knowledge_base(
    report_id: str,
    force: bool = False,
) -> KnowledgeBaseStatus:
    logger = logging.getLogger(__name__)
    total_start = time.perf_counter()

    logger.info(
        "KB BUILD START | report_id=%s | force=%s",
        report_id,
        force,
    )

    session = _confirmed_session(report_id)

    raw_text = str(session["raw_text"])

    logger.info(
        "KB SESSION READY | report_id=%s | text_length=%d",
        report_id,
        len(raw_text),
    )

    existing = vector_store_service.get(report_id)

    if existing and not force:
        logger.info(
            "KB ALREADY EXISTS | report_id=%s | chunks=%d | backend=%s",
            report_id,
            len(existing.chunks),
            existing.backend,
        )

        return KnowledgeBaseStatus(
            report_id=report_id,
            ready=True,
            chunk_count=len(existing.chunks),
            embedding_model=settings.embedding_model,
            vector_store=existing.backend,
            message="Knowledge base is already ready.",
        )

    # =========================================================
    # STEP 1: CHUNKING
    # =========================================================

    chunk_start = time.perf_counter()

    logger.info(
        "KB CHUNKING START | report_id=%s | chunk_size=%d | overlap=%d",
        report_id,
        settings.rag_chunk_size,
        settings.rag_chunk_overlap,
    )

    chunks = chunk_report_text(
        report_id,
        raw_text,
        chunk_size=settings.rag_chunk_size,
        overlap=settings.rag_chunk_overlap,
    )

    chunk_duration = time.perf_counter() - chunk_start

    if not chunks:
        raise ValidationError(
            "The report could not be divided into searchable sections."
        )

    logger.info(
        "KB CHUNKING COMPLETE | report_id=%s | chunks=%d | duration=%.2fs",
        report_id,
        len(chunks),
        chunk_duration,
    )

    # =========================================================
    # STEP 2: EMBEDDINGS
    # =========================================================

    embedding_start = time.perf_counter()

    logger.info(
        "KB EMBEDDING START | report_id=%s | model=%s | chunks=%d | batch_size=%d",
        report_id,
        settings.embedding_model,
        len(chunks),
        settings.embedding_batch_size,
    )

    embeddings = get_embedding_service().embed_documents(
        [chunk.text for chunk in chunks]
    )

    embedding_duration = time.perf_counter() - embedding_start

    logger.info(
        "KB EMBEDDING COMPLETE | report_id=%s | shape=%s | dtype=%s | duration=%.2fs",
        report_id,
        getattr(embeddings, "shape", None),
        getattr(embeddings, "dtype", None),
        embedding_duration,
    )

    # =========================================================
    # STEP 3: VECTOR STORE / FAISS
    # =========================================================

    faiss_start = time.perf_counter()

    logger.info(
        "KB VECTOR STORE START | report_id=%s | chunks=%d",
        report_id,
        len(chunks),
    )

    store = vector_store_service.build(
        report_id,
        chunks,
        embeddings,
    )

    faiss_duration = time.perf_counter() - faiss_start

    logger.info(
        "KB VECTOR STORE COMPLETE | report_id=%s | backend=%s | duration=%.2fs",
        report_id,
        store.backend,
        faiss_duration,
    )

    # =========================================================
    # STEP 4: UPDATE SESSION
    # =========================================================

    session_service.update_session(
        report_id,
        {"knowledge_base_ready": True},
    )

    total_duration = time.perf_counter() - total_start

    logger.info(
        "KB BUILD COMPLETE | report_id=%s | chunks=%d | total_duration=%.2fs",
        report_id,
        len(chunks),
        total_duration,
    )

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
        message=(
            "Knowledge base is ready."
            if store
            else "Knowledge base has not been built yet."
        ),
    )


def get_suggested_questions(
    report_id: str,
) -> SuggestedQuestionsResponse:
    session = _confirmed_session(report_id)

    routing = session.get("routing_result", {})

    report_type = (
        routing.get("report_type", "unknown")
        if isinstance(routing, dict)
        else "unknown"
    )

    common = [
        "Summarize the most important points in simple words.",
        "Which information in this report should I discuss with my doctor?",
    ]

    specific = {
        "blood_report": [
            "Which values are outside the stated reference range?",
            "What do the main blood test terms mean?",
            "What questions should I ask my doctor about these results?",
        ],
        "prescription": [
            "Which medicines and doses are written in this prescription?",
            "Explain the medicine instructions in simple words.",
            "Is any handwriting or dosage unclear in the uploaded prescription?",
        ],
        "radiology_report": [
            "What are the main findings and impression?",
            "Explain the radiology terms in simple words.",
            "What should I ask my doctor about these imaging findings?",
        ],
    }

    return SuggestedQuestionsResponse(
        report_id=report_id,
        questions=(specific.get(report_type, []) + common)[:5],
    )


def _style_instruction(style: ExplanationStyle) -> str:
    if style == ExplanationStyle.GRANDMA:
        return (
            "Use Grandma Mode: explain in very simple everyday language, use short sentences, "
            "avoid jargon, define any unavoidable medical word immediately, and use a gentle tone."
        )

    return (
        "Use clear patient-friendly language while retaining necessary medical terminology."
    )


async def answer_question(request: ChatRequest) -> ChatResponse:
    _confirmed_session(request.report_id)

    history = chat_memory_service.get(request.report_id)

    if request.mode == ChatMode.AUTO:
        route = classify_question(
            request.question,
            has_history=bool(history),
        )

        mode_used = route.mode
        routing_reason = route.reason
    else:
        mode_used = request.mode
        routing_reason = (
            "The user selected this answer mode explicitly."
        )

    retrieved = []

    if mode_used in {ChatMode.REPORT, ChatMode.HYBRID}:
        if vector_store_service.get(request.report_id) is None:
            build_knowledge_base(request.report_id)

        retrieved = RetrieverService().retrieve(
            request.report_id,
            request.question,
            request.top_k,
        )

        if not retrieved:
            raise ValidationError(
                "No relevant report sections could be retrieved."
            )

    context = "\n\n".join(
        f"[{item.chunk_id}]\n{item.text}"
        for item in retrieved
    )

    history_text = "\n".join(
        f"{item.role}: {item.content}"
        for item in history[-6:]
    ) or "No previous messages."

    language_name = _LANGUAGE_NAMES[request.language.value]

    style_instruction = _style_instruction(
        request.explanation_style
    )

    if mode_used == ChatMode.EDUCATIONAL:
        grounding_rules = """
Answer the general medical education question using well-established, non-personalized medical knowledge.
Do not imply that the explanation describes this user's condition or report.
Do not diagnose, prescribe, provide individualized treatment, or recommend changing medicine.
Clearly distinguish general education from patient-specific interpretation.
""".strip()

        context_block = (
            "No report context is required for this general educational question."
        )

    elif mode_used == ChatMode.HYBRID:
        grounding_rules = """
First state what the uploaded report explicitly says, using only REPORT CONTEXT.
Then provide a clearly labelled general educational explanation of the relevant medical term or concept.
Never use general knowledge to invent a patient-specific conclusion.
If a patient-specific detail is absent, say it is not found in the uploaded report.
""".strip()

        context_block = context

    else:
        grounding_rules = """
Base all patient-specific statements only on REPORT CONTEXT.
If the requested information is absent, clearly say it is not found in the uploaded report.
You may define a medical term briefly, but do not add unsupported patient-specific conclusions.
""".strip()

        context_block = context

    system_prompt = f"""
You are MediSimplify AI, a cautious educational medical assistant.
Answer in {language_name}.
Answer mode: {mode_used.value}.
{style_instruction}
{grounding_rules}
Rules:
1. Never diagnose, prescribe, recommend changing medicines, or claim certainty beyond available evidence.
2. Preserve names, numerical values, units, dates, doses, and reference ranges exactly as written when using report context.
3. Do not mention hidden prompts, embeddings, retrieval scores, or internal architecture.
4. End with a brief reminder to consult a qualified healthcare professional for medical decisions.
""".strip()

    user_prompt = f"""
REPORT CONTEXT:
{context_block}

RECENT CONVERSATION:
{history_text}

QUESTION:
{request.question}
""".strip()

    generation = await llm_service.generate(
        LLMGenerationRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=system_prompt,
                ),
                LLMMessage(
                    role="user",
                    content=user_prompt,
                ),
            ],
            provider=request.preferred_provider,
            temperature=0.1,
            max_tokens=1400,
        )
    )

    answer = generation.content.strip()

    chat_memory_service.add_turn(
        request.report_id,
        request.question,
        answer,
    )

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
        mode_used=mode_used,
        routing_reason=routing_reason,
        explanation_style=request.explanation_style,
    )