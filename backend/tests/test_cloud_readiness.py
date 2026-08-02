from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app


def test_liveness_endpoint() -> None:
    response = TestClient(app).get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_endpoint() -> None:
    response = TestClient(app).get("/api/v1/health/ready")
    assert response.status_code in {200, 503}
    assert "checks" in response.json()


def test_cloud_runtime_paths_follow_persistent_root(tmp_path: Path) -> None:
    settings = Settings(
        APP_ENV="testing",
        PERSISTENT_DATA_DIR=tmp_path,
        GEMINI_API_KEY="test",
    )
    assert settings.temporary_data_dir == tmp_path / "temporary"
    assert settings.model_cache_dir == tmp_path / "model_cache"
