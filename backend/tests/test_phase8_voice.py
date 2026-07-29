from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.services import voice_service

client = TestClient(app)


def test_voice_status_endpoint():
    response = client.get("/api/v1/voice/status")
    assert response.status_code == 200
    payload = response.json()
    assert "transcription_enabled" in payload
    assert "speech_enabled" in payload
    assert payload["transcription_model"]


def test_transcription_endpoint(monkeypatch):
    monkeypatch.setattr(
        voice_service,
        "transcribe_audio",
        lambda content, filename, language=None: {
            "text": "What is my haemoglobin value?",
            "language": "en",
            "duration_seconds": 2.4,
            "model": "small",
        },
    )
    response = client.post(
        "/api/v1/voice/transcribe",
        files={"audio": ("voice.wav", b"fake-wave", "audio/wav")},
        data={"language": "english"},
    )
    assert response.status_code == 200
    assert response.json()["text"].startswith("What is")


def test_speech_endpoint(monkeypatch):
    monkeypatch.setattr(
        voice_service,
        "synthesize_speech",
        lambda text, language, slow=False: b"fake-mp3",
    )
    response = client.post(
        "/api/v1/voice/speak",
        json={"text": "Your report explanation", "language": "english", "slow": False},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.content == b"fake-mp3"
