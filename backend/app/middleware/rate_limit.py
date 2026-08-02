from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import settings


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    """Small single-instance rate limiter suitable for the first production release.

    Cloud deployments with multiple replicas should replace this with a shared Redis
    limiter. Health and documentation routes are intentionally excluded.
    """

    def __init__(self, app):
        super().__init__(app)
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    @staticmethod
    def _client_key(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        host = forwarded or (request.client.host if request.client else "unknown")
        return host[:128]

    @staticmethod
    def _policy(request: Request) -> tuple[str, int] | None:
        if request.method == "POST" and request.url.path.endswith("/reports/extract"):
            return "upload", settings.rate_limit_uploads_per_minute
        if request.method == "POST" and request.url.path.endswith("/chat"):
            return "chat", settings.rate_limit_questions_per_minute
        if request.method == "POST" and "/voice/" in request.url.path:
            return "voice", settings.rate_limit_voice_per_minute
        return None

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.rate_limit_enabled or settings.app_env == "testing":
            return await call_next(request)

        policy = self._policy(request)
        if policy is None:
            return await call_next(request)

        bucket, limit = policy
        now = time.monotonic()
        key = f"{bucket}:{self._client_key(request)}"
        async with self._lock:
            events = self._events[key]
            while events and now - events[0] >= 60:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(60 - (now - events[0])))
                request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
                request.state.request_id = request_id
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(retry_after), "X-Request-ID": request_id},
                    content={
                        "status": "error",
                        "error_type": "RateLimitExceeded",
                        "message": "Too many requests. Please wait briefly and try again.",
                        "request_id": request_id,
                    },
                )
            events.append(now)

        return await call_next(request)
