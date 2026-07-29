import pytest

from app.core.config import settings
from app.models.llm_models import LLMGenerationResult, ProviderName
from app.services import multimodal_service


@pytest.mark.asyncio
async def test_local_image_fallback_uses_configured_structuring_provider(monkeypatch):
    monkeypatch.setattr(settings, "local_ocr_enabled", True)
    monkeypatch.setattr(settings, "ocr_structuring_provider", "groq")
    monkeypatch.setattr(
        multimodal_service.local_ocr_service,
        "extract_text_from_image",
        lambda _: "Haemoglobin 10.2 g/dL",
    )

    async def fake_generate(request):
        assert request.provider == ProviderName.GROQ
        return LLMGenerationResult(
            provider=ProviderName.GROQ,
            model="test-model",
            content='{"document_type_hint":"blood_report"}',
            parsed_json={
                "document_type_hint": "blood_report",
                "extracted_text": "Haemoglobin 10.2 g/dL",
                "patient_information": {},
                "sections": [],
                "medicine_items": [],
                "radiology_findings": [],
                "unreadable_text": [],
                "warnings": [],
            },
        )

    monkeypatch.setattr(multimodal_service.llm_service, "generate", fake_generate)
    result = await multimodal_service._local_image_fallback(
        "report.png", RuntimeError("429 quota exceeded")
    )

    assert result.document_type_hint == "blood_report"
    assert "local Tesseract OCR" in result.warnings[0]


@pytest.mark.asyncio
async def test_text_extraction_uses_provider_abstraction(monkeypatch):
    async def fake_generate(request):
        assert request.require_json is True
        return LLMGenerationResult(
            provider=ProviderName.OLLAMA,
            model="llama3.2:3b",
            content='{"document_type_hint":"unknown"}',
            parsed_json={
                "document_type_hint": "unknown",
                "extracted_text": "Sample report text",
                "patient_information": {},
                "sections": [],
                "medicine_items": [],
                "radiology_findings": [],
                "unreadable_text": [],
                "warnings": [],
            },
        )

    monkeypatch.setattr(multimodal_service.llm_service, "generate", fake_generate)
    result = await multimodal_service.extract_structured_from_text("Sample report text")
    assert result.extracted_text == "Sample report text"
