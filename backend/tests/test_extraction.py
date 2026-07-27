from io import BytesIO

from PIL import Image

from app.models.extraction_models import ExtractionResult
from app.services import session_service


def sample_result(text: str = "Haemoglobin: 10.2 g/dL") -> ExtractionResult:
    return ExtractionResult(
        document_type_hint="blood_report",
        extracted_text=text,
        sections=[
            {
                "section_name": "CBC",
                "items": [
                    {
                        "label": "Haemoglobin",
                        "value": "10.2",
                        "unit": "g/dL",
                        "reference_range": "12-15",
                    }
                ],
            }
        ],
    )


def test_extract_txt_report(client, monkeypatch):
    async def fake_text_extraction(raw_text: str):
        assert "Haemoglobin" in raw_text
        return sample_result(raw_text)

    monkeypatch.setattr(
        "app.api.routes_extraction.multimodal_service.extract_structured_from_text",
        fake_text_extraction,
    )

    response = client.post(
        "/api/v1/reports/extract",
        files={
            "file": (
                "report.txt",
                b"Haemoglobin: 10.2 g/dL\nReference range: 12-15 g/dL",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["input_type"] == "document"
    assert payload["requires_confirmation"] is True
    assert payload["structured_data"]["document_type_hint"] == "blood_report"
    assert session_service.get_session(payload["report_id"])


def test_extract_image_report(client, monkeypatch):
    image = Image.new("RGB", (1000, 1200), "white")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")

    monkeypatch.setattr(
        "app.api.routes_extraction.image_validation_service.check_image_quality",
        lambda _: {
            "status": "clear",
            "issues": [],
            "can_continue": True,
            "recommendation": "Image quality is sufficient.",
        },
    )

    async def fake_image_extraction(file_path: str, mime_type: str):
        assert mime_type == "image/png"
        return sample_result()

    monkeypatch.setattr(
        "app.api.routes_extraction.multimodal_service.extract_structured_from_image",
        fake_image_extraction,
    )

    response = client.post(
        "/api/v1/reports/extract",
        files={"file": ("report.png", image_bytes.getvalue(), "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["input_type"] == "image"


def test_reject_unsupported_file(client):
    response = client.post(
        "/api/v1/reports/extract",
        files={"file": ("malware.exe", b"not valid", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["message"]


def test_reject_empty_file(client):
    response = client.post(
        "/api/v1/reports/extract",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["message"].lower()


def test_confirm_extraction(client):
    report_id = "test-confirm-report"
    session_service.create_session(
        report_id,
        {"raw_text": "Original", "structured_data": {}, "confirmed": False},
    )

    response = client.post(
        f"/api/v1/reports/{report_id}/confirm-analysis",
        json={
            "confirmed_text": "Corrected report text",
            "corrected_structured_data": {
                "document_type_hint": "unknown",
                "extracted_text": "Corrected report text",
            },
            "language": "pa",
            "provider": "gemini",
        },
    )

    assert response.status_code == 200
    stored = session_service.get_session(report_id)
    assert stored["confirmed"] is True
    assert stored["raw_text"] == "Corrected report text"
    assert stored["language"] == "pa"


def test_confirm_missing_report(client):
    response = client.post(
        "/api/v1/reports/missing-report/confirm-analysis",
        json={
            "confirmed_text": "Text",
            "corrected_structured_data": {},
            "language": "en",
            "provider": "gemini",
        },
    )
    assert response.status_code == 404
