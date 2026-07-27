from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.analysis_models import AgentStructuredOutput, AnalysisItem, AnalysisLanguage
from app.models.llm_models import ProviderName
from app.models.routing_models import AgentName, ReportType, RoutingResult
from app.services import analysis_service, session_service

client = TestClient(app)


def sample_output() -> AgentStructuredOutput:
    return AgentStructuredOutput(
        summary="This is an educational explanation of the written report.",
        items=[
            AnalysisItem(
                name="Hemoglobin",
                observed_value="10.2",
                unit="g/dL",
                reference_range="12-15",
                status="low",
                simple_explanation="Hemoglobin carries oxygen in the blood.",
            )
        ],
        important_notes=["The value is reproduced exactly as written."],
        unclear_information=[],
        questions_for_doctor=["What does this result mean in my situation?"],
        disclaimer="Educational only; this is not a diagnosis or replacement for a doctor.",
    )


@pytest.mark.asyncio
async def test_analysis_service_uses_blood_agent(monkeypatch) -> None:
    mocked = AsyncMock(
        return_value=(sample_output(), ProviderName.GEMINI, "gemini-test", False)
    )
    monkeypatch.setattr("app.agents.blood_agent.BloodReportAgent.explain", mocked)
    route = RoutingResult(
        report_id="blood-1",
        report_type=ReportType.BLOOD_REPORT,
        confidence=0.92,
        selected_agent=AgentName.BLOOD_AGENT,
        reason="Laboratory indicators found.",
        method="rules",
    )
    result = await analysis_service.explain_report(
        report_id="blood-1",
        confirmed_text="Hemoglobin 10.2 g/dL reference range 12-15",
        routing_result=route,
        language=AnalysisLanguage.ENGLISH,
        preferred_provider=ProviderName.GEMINI,
    )
    assert result.agent_used == AgentName.BLOOD_AGENT
    assert result.items[0].observed_value == "10.2"
    mocked.assert_awaited_once()


@pytest.mark.asyncio
async def test_analysis_requires_manual_route_to_be_resolved() -> None:
    route = RoutingResult(
        report_id="mixed-1",
        report_type=ReportType.MIXED_REPORT,
        confidence=0.5,
        selected_agent=AgentName.FALLBACK_AGENT,
        reason="Mixed content.",
        requires_manual_selection=True,
        method="rules",
    )
    with pytest.raises(Exception):
        await analysis_service.explain_report(
            "mixed-1", "mixed text", route, AnalysisLanguage.ENGLISH
        )


def test_explain_endpoint_requires_session() -> None:
    response = client.post(
        "/api/v1/analysis/explain",
        json={"report_id": "missing", "language": "english"},
    )
    assert response.status_code == 404


def test_explain_endpoint_requires_route() -> None:
    session_service.create_session(
        "no-route", {"confirmed": True, "raw_text": "Hemoglobin 10.2 g/dL"}
    )
    response = client.post(
        "/api/v1/analysis/explain",
        json={"report_id": "no-route", "language": "english"},
    )
    assert response.status_code == 400
    session_service.delete_session("no-route")


def test_explain_endpoint_success(monkeypatch) -> None:
    route = RoutingResult(
        report_id="ready-1",
        report_type=ReportType.BLOOD_REPORT,
        confidence=0.9,
        selected_agent=AgentName.BLOOD_AGENT,
        reason="Blood report.",
        method="rules",
    )
    session_service.create_session(
        "ready-1",
        {
            "confirmed": True,
            "raw_text": "Hemoglobin 10.2 g/dL",
            "routing_result": route.model_dump(),
        },
    )
    expected = analysis_service.ReportAnalysisResponse(
        report_id="ready-1",
        report_type=ReportType.BLOOD_REPORT,
        agent_used=AgentName.BLOOD_AGENT,
        provider_used=ProviderName.GEMINI,
        model="gemini-test",
        language=AnalysisLanguage.ENGLISH,
        summary=sample_output().summary,
        items=sample_output().items,
        important_notes=sample_output().important_notes,
        unclear_information=[],
        questions_for_doctor=sample_output().questions_for_doctor,
        disclaimer=sample_output().disclaimer,
    )
    monkeypatch.setattr(
        analysis_service,
        "explain_report",
        AsyncMock(return_value=expected),
    )
    response = client.post(
        "/api/v1/analysis/explain",
        json={
            "report_id": "ready-1",
            "language": "english",
            "preferred_provider": "gemini",
        },
    )
    assert response.status_code == 200
    assert response.json()["agent_used"] == "blood_agent"
    assert response.json()["items"][0]["name"] == "Hemoglobin"
    session_service.delete_session("ready-1")
