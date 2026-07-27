from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.agents.supervisor_agent import SupervisorAgent
from app.main import app
from app.models.llm_models import ProviderName
from app.models.routing_models import ReportType, RoutingResult
from app.services import routing_service, session_service

client = TestClient(app)


@pytest.mark.asyncio
async def test_rules_route_clear_blood_report_without_llm(monkeypatch) -> None:
    classify = AsyncMock()
    monkeypatch.setattr(SupervisorAgent, "classify", classify)
    result = await routing_service.route_report(
        "blood-1",
        "CBC Hemoglobin 12 g/dL WBC 7000 cells/cumm Platelets 250000 reference range",
    )
    assert result.report_type == ReportType.BLOOD_REPORT
    assert result.selected_agent.value == "blood_agent"
    assert result.method == "rules"
    classify.assert_not_awaited()


@pytest.mark.asyncio
async def test_rules_route_clear_prescription() -> None:
    result = await routing_service.route_report(
        "rx-1",
        "Rx Tablet Paracetamol 500 mg twice daily after food for days dosage",
    )
    assert result.report_type == ReportType.PRESCRIPTION
    assert result.selected_agent.value == "prescription_agent"


@pytest.mark.asyncio
async def test_uncertain_text_uses_supervisor(monkeypatch) -> None:
    expected = RoutingResult(
        report_id="r-1",
        report_type="radiology_report",
        confidence=0.8,
        selected_agent="radiology_agent",
        reason="Radiology wording detected.",
        method="llm",
        provider_used=ProviderName.GEMINI,
    )
    monkeypatch.setattr(SupervisorAgent, "classify", AsyncMock(return_value=expected))
    result = await routing_service.route_report("r-1", "Clinical document with limited wording")
    assert result == expected


def test_route_endpoint_requires_existing_session() -> None:
    response = client.post("/api/v1/analysis/route", json={"report_id": "missing"})
    assert response.status_code == 404


def test_route_endpoint_requires_confirmation() -> None:
    session_service.create_session("not-confirmed", {"confirmed": False, "raw_text": "CBC test"})
    response = client.post("/api/v1/analysis/route", json={"report_id": "not-confirmed"})
    assert response.status_code == 400
    session_service.delete_session("not-confirmed")


def test_route_endpoint_routes_confirmed_report() -> None:
    session_service.create_session(
        "confirmed-blood",
        {
            "confirmed": True,
            "raw_text": "CBC Hemoglobin 12 g/dL WBC 7000 cells/cumm Platelets reference range",
        },
    )
    response = client.post(
        "/api/v1/analysis/route",
        json={"report_id": "confirmed-blood", "preferred_provider": "gemini"},
    )
    assert response.status_code == 200
    assert response.json()["report_type"] == "blood_report"
    session_service.delete_session("confirmed-blood")


def test_manual_route_endpoint() -> None:
    session_service.create_session("manual-1", {"confirmed": True, "raw_text": "unclear report"})
    response = client.post(
        "/api/v1/analysis/manual-1/manual-route",
        json={"report_type": "radiology_report"},
    )
    assert response.status_code == 200
    assert response.json()["method"] == "manual"
    assert response.json()["selected_agent"] == "radiology_agent"
    session_service.delete_session("manual-1")
