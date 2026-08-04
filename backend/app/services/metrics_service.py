from __future__ import annotations

import os
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _MetricsState:
    started_at: float = field(default_factory=time.time)
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    active_requests: int = 0
    total_response_ms: float = 0.0
    slow_requests: int = 0
    category_requests: Counter[str] = field(default_factory=Counter)
    provider_usage: Counter[str] = field(default_factory=Counter)
    provider_failures: Counter[str] = field(default_factory=Counter)


class MetricsService:
    """Thread-safe, process-local application metrics for one backend instance."""

    def __init__(self) -> None:
        self._state = _MetricsState()
        self._lock = threading.RLock()

    def request_started(self, category: str) -> None:
        with self._lock:
            self._state.total_requests += 1
            self._state.active_requests += 1
            self._state.category_requests[category] += 1

    def request_finished(self, *, status_code: int, duration_ms: float, slow: bool) -> None:
        with self._lock:
            self._state.active_requests = max(0, self._state.active_requests - 1)
            self._state.total_response_ms += max(0.0, duration_ms)
            if status_code < 400:
                self._state.successful_requests += 1
            else:
                self._state.failed_requests += 1
            if slow:
                self._state.slow_requests += 1

    def provider_succeeded(self, provider: str) -> None:
        with self._lock:
            self._state.provider_usage[provider] += 1

    def provider_failed(self, provider: str) -> None:
        with self._lock:
            self._state.provider_failures[provider] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = self._state
            average_ms = (
                state.total_response_ms / state.total_requests
                if state.total_requests
                else 0.0
            )
            payload: dict[str, Any] = {
                "uptime_seconds": round(max(0.0, time.time() - state.started_at), 2),
                "total_requests": state.total_requests,
                "successful_requests": state.successful_requests,
                "failed_requests": state.failed_requests,
                "active_requests": state.active_requests,
                "average_response_ms": round(average_ms, 2),
                "slow_requests": state.slow_requests,
                "request_categories": dict(sorted(state.category_requests.items())),
                "provider_usage": dict(sorted(state.provider_usage.items())),
                "provider_failures": dict(sorted(state.provider_failures.items())),
            }
            memory_mb = _process_memory_mb()
            if memory_mb is not None:
                payload["process_memory_mb"] = memory_mb
            return payload

    def reset_for_tests(self) -> None:
        with self._lock:
            self._state = _MetricsState()


def _process_memory_mb() -> float | None:
    """Return best-effort resident memory without adding a runtime dependency."""
    try:
        import resource

        value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        # Linux reports KiB, macOS reports bytes.
        if os.name == "posix" and value < 10_000_000:
            return round(value / 1024.0, 2)
        return round(value / (1024.0 * 1024.0), 2)
    except (ImportError, OSError, ValueError):
        return None


metrics_service = MetricsService()
