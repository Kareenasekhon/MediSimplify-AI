from __future__ import annotations

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


@router.get("/health/ready", tags=["Health"])
async def get_readiness(response: Response) -> dict:
    """Confirm that required runtime storage and provider configuration are ready."""
    checks: dict[str, bool] = {}

    try:
        Path(settings.temporary_data_dir).mkdir(parents=True, exist_ok=True)
        probe = Path(settings.temporary_data_dir) / ".readiness"
        probe.write_text("ready", encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks["temporary_storage"] = True
    except OSError:
        checks["temporary_storage"] = False

    checks["llm_provider"] = bool(settings.configured_providers)
    ready = all(checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready else "not_ready",
        "service": constants.PROJECT_NAME,
        "version": constants.VERSION,
        "environment": settings.app_env,
        "checks": checks,
    }
