from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Response, status

from app.core import constants
from app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["Health"])
async def get_health() -> dict:
    """Backward-compatible service health endpoint."""
    return {
        "status": "healthy",
        "service": constants.PROJECT_NAME,
        "version": constants.VERSION,
    }


@router.get("/health/live", tags=["Health"])
async def get_liveness() -> dict:
    """Confirm that the FastAPI process is alive."""
    return {
        "status": "alive",
        "service": constants.PROJECT_NAME,
        "version": constants.VERSION,
    }


def _storage_ready() -> bool:
    try:
        Path(settings.temporary_data_dir).mkdir(parents=True, exist_ok=True)
        probe = Path(settings.temporary_data_dir) / ".readiness"
        probe.write_text("ready", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


@router.get("/health/ready", tags=["Health"])
async def get_readiness(response: Response) -> dict:
    """Return a secret-free summary of runtime dependencies and capabilities."""
    tesseract = settings.tesseract_cmd or shutil.which("tesseract")
    vector_path = Path(settings.persistent_data_dir)
    try:
        vector_path.mkdir(parents=True, exist_ok=True)
        vector_store_ready = vector_path.exists() and vector_path.is_dir()
    except OSError:
        vector_store_ready = False

    checks: dict[str, bool] = {
        "temporary_storage": _storage_ready(),
        "llm_provider": bool(settings.configured_providers),
        "vector_store": vector_store_ready,
        "ocr": (not settings.local_ocr_enabled) or bool(tesseract),
        "voice": (not settings.voice_transcription_enabled) or bool(settings.voice_whisper_model),
    }

    # Only storage and an LLM provider are mandatory for accepting core traffic.
    ready = checks["temporary_storage"] and checks["llm_provider"]
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready else "not_ready",
        "service": constants.PROJECT_NAME,
        "version": constants.VERSION,
        "environment": settings.app_env,
        "checks": checks,
    }
