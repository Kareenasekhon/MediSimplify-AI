from io import BytesIO


def test_security_headers_and_request_id(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers.get("x-request-id")


def test_reject_file_with_mismatched_signature(client):
    response = client.post(
        "/api/v1/reports/extract",
        files={"file": ("fake.pdf", b"MZ-not-a-pdf", "application/pdf")},
    )
    assert response.status_code == 400
    assert "do not match" in response.json()["message"]
    assert response.json().get("request_id")


def test_reject_invalid_report_id(client):
    response = client.get("/api/v1/chat/../../bad/status")
    assert response.status_code in {404, 400}


def test_reject_non_audio_upload(client):
    response = client.post(
        "/api/v1/voice/transcribe",
        files={"audio": ("voice.exe", BytesIO(b"abc"), "application/octet-stream")},
        data={"language": "english"},
    )
    assert response.status_code == 400
    assert "Unsupported audio format" in response.json()["message"]
