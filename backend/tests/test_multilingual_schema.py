from unittest.mock import AsyncMock

import pytest

from app.agents.common_report_agent import PromptDrivenReportAgent
from app.models.analysis_models import AnalysisLanguage
from app.models.llm_models import LLMGenerationResult, ProviderName


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "language, translated_summary",
    [
        (AnalysisLanguage.HINDI, "यह रिपोर्ट शैक्षिक रूप से समझाई गई है।"),
        (AnalysisLanguage.PUNJABI, "ਇਸ ਰਿਪੋਰਟ ਦੀ ਸਿੱਖਿਆਤਮਕ ਵਿਆਖਿਆ ਦਿੱਤੀ ਗਈ ਹੈ।"),
    ],
)
async def test_multilingual_output_keeps_english_schema_keys(
    monkeypatch,
    language,
    translated_summary,
) -> None:
    valid_json = {
        "summary": translated_summary,
        "items": [
            {
                "name": "Hemoglobin",
                "observed_value": "10.2",
                "unit": "g/dL",
                "reference_range": "12-15",
                "status": "low",
                "dosage": None,
                "frequency": None,
                "duration": None,
                "section": "CBC",
                "simple_explanation": translated_summary,
                "source_text": "Hemoglobin 10.2 g/dL",
            }
        ],
        "important_notes": [],
        "unclear_information": [],
        "questions_for_doctor": [],
        "disclaimer": translated_summary,
    }

    generate_mock = AsyncMock(
        return_value=LLMGenerationResult(
            provider=ProviderName.GEMINI,
            model="gemini-test",
            content="{}",
            parsed_json=valid_json,
            fallback_used=False,
            attempts=1,
        )
    )
    monkeypatch.setattr(
        "app.agents.common_report_agent.llm_service.generate",
        generate_mock,
    )

    agent = PromptDrivenReportAgent("Explain blood reports.")
    output, provider, model, fallback = await agent.explain(
        confirmed_text="Hemoglobin 10.2 g/dL",
        language=language,
        provider=ProviderName.GEMINI,
    )

    assert output.summary == translated_summary
    assert output.items[0].name == "Hemoglobin"
    assert provider == ProviderName.GEMINI
    assert model == "gemini-test"
    assert fallback is False
    assert generate_mock.await_count == 1


@pytest.mark.asyncio
async def test_invalid_multilingual_schema_is_repaired(monkeypatch) -> None:
    invalid_json = {
        "सारांश": "रिपोर्ट की व्याख्या।",
        "items": "not-an-array",
    }
    repaired_json = {
        "summary": "रिपोर्ट की शैक्षिक व्याख्या।",
        "items": [],
        "important_notes": [],
        "unclear_information": [],
        "questions_for_doctor": [],
        "disclaimer": "यह केवल शैक्षिक जानकारी है, निदान नहीं।",
    }

    generate_mock = AsyncMock(
        side_effect=[
            LLMGenerationResult(
                provider=ProviderName.GEMINI,
                model="gemini-test",
                content="{}",
                parsed_json=invalid_json,
                fallback_used=False,
                attempts=1,
            ),
            LLMGenerationResult(
                provider=ProviderName.GEMINI,
                model="gemini-test",
                content="{}",
                parsed_json=repaired_json,
                fallback_used=False,
                attempts=1,
            ),
        ]
    )
    monkeypatch.setattr(
        "app.agents.common_report_agent.llm_service.generate",
        generate_mock,
    )

    agent = PromptDrivenReportAgent("Explain blood reports.")
    output, _, _, _ = await agent.explain(
        confirmed_text="Hemoglobin 10.2 g/dL",
        language=AnalysisLanguage.HINDI,
        provider=ProviderName.GEMINI,
    )

    assert output.summary == repaired_json["summary"]
    assert generate_mock.await_count == 2
