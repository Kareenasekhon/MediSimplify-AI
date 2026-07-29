import pytest

from app.models.chat_models import ChatMode, ChatRequest, ExplanationStyle
from app.models.llm_models import LLMGenerationResult, ProviderName
from app.services import rag_service, session_service
from app.services.chat_memory_service import chat_memory_service
from app.services.question_router_service import classify_question
from app.services.vector_store_service import vector_store_service


def test_question_router_distinguishes_general_report_and_hybrid():
    assert classify_question("What is radiology?").mode == ChatMode.EDUCATIONAL
    assert classify_question("What is my hemoglobin value?").mode == ChatMode.HYBRID
    assert classify_question("Is my platelet count normal?").mode == ChatMode.REPORT


@pytest.mark.asyncio
async def test_general_education_does_not_require_vector_search(monkeypatch):
    report_id = "phase7-general"
    session_service.create_session(
        report_id,
        {
            "report_id": report_id,
            "confirmed": True,
            "raw_text": "MRI lumbar spine report. Impression: mild disc bulge.",
        },
    )
    vector_store_service.delete(report_id)
    chat_memory_service.clear(report_id)

    async def fake_generate(request):
        prompt = request.messages[0].content
        assert "educational" in prompt
        assert "Grandma Mode" in prompt
        return LLMGenerationResult(
            provider=ProviderName.GEMINI,
            model="fake-model",
            content="Radiology uses medical images to help doctors understand the body.",
        )

    monkeypatch.setattr(rag_service.llm_service, "generate", fake_generate)

    response = await rag_service.answer_question(
        ChatRequest(
            report_id=report_id,
            question="What is radiology?",
            mode=ChatMode.AUTO,
            explanation_style=ExplanationStyle.GRANDMA,
        )
    )

    assert response.mode_used == ChatMode.EDUCATIONAL
    assert response.explanation_style == ExplanationStyle.GRANDMA
    assert response.sources == []
    assert vector_store_service.get(report_id) is None


def test_suggested_questions_follow_report_type():
    report_id = "phase7-suggestions"
    session_service.create_session(
        report_id,
        {
            "report_id": report_id,
            "confirmed": True,
            "raw_text": "Hemoglobin: 10.2 g/dL",
            "routing_result": {"report_type": "blood_report"},
        },
    )

    result = rag_service.get_suggested_questions(report_id)

    assert result.questions
    assert any("reference range" in question.lower() for question in result.questions)
