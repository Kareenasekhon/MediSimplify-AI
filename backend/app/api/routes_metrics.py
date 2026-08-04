from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.services.metrics_service import metrics_service

router = APIRouter(tags=["Monitoring"])


def _metrics_payload() -> dict:
    if not settings.metrics_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metrics are disabled.",
        )
    return metrics_service.snapshot()


@router.get("/metrics")
async def get_metrics() -> dict:
    """Return secret-free, process-local operational metrics."""
    return _metrics_payload()


@router.get("/api/v1/metrics", include_in_schema=False)
async def get_versioned_metrics() -> dict:
    """Versioned alias retained for API clients."""
    return _metrics_payload()
