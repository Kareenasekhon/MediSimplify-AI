from __future__ import annotations

import time

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.services.metrics_service import metrics_service


def _category(path: str) -> str:
    if "/extraction" in path:
        return "ocr"
    if "/analysis" in path or path.endswith("/route"):
        return "analysis"
    if "/chat" in path:
        return "chat"
    if "/voice" in path:
        return "voice"
    if "/providers" in path:
        return "provider"
    if "/health" in path:
        return "health"
    if path.endswith("/metrics"):
        return "metrics"
    return "other"


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Collect aggregate metrics and emit request-aware structured log events."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        category = _category(path)
        should_measure = not (
            settings.metrics_exclude_health_checks and category in {"health", "metrics"}
        )
        if should_measure:
            metrics_service.request_started(category)

        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            slow = duration_ms >= settings.slow_request_threshold_ms
            request_id = getattr(request.state, "request_id", "unavailable")

            if should_measure:
                metrics_service.request_finished(
                    status_code=status_code,
                    duration_ms=duration_ms,
                    slow=slow,
                )

            log = logger.warning if slow else logger.info
            log(
                "HTTP request | method={} | path={} | status={} | duration_ms={:.2f} | request_id={} | category={}",
                request.method,
                path,
                status_code,
                duration_ms,
                request_id,
                category,
            )
