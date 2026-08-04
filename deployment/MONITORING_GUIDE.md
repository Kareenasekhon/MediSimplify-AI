# MediSimplify AI Monitoring Guide

Phase 10.3 Batch 4 adds lightweight, process-local observability for a single backend instance.

## Endpoints

- `GET /metrics` — aggregate request and provider metrics.
- `GET /api/v1/metrics` — versioned alias.
- `GET /api/v1/health/live` — process liveness.
- `GET /api/v1/health/ready` — storage, provider, OCR, vector-store, and voice readiness summary.

The metrics response contains no prompts, report text, filenames, API keys, or patient data.

## Important limitation

Metrics are stored in memory. They reset whenever the backend container restarts and are not combined across multiple replicas. For multi-instance production deployment, replace this layer with Prometheus/OpenTelemetry and a central metrics backend.

## Slow requests

Set `SLOW_REQUEST_THRESHOLD_MS` to control warning logs. Requests at or above this duration are logged at warning level with method, path, status, duration, request ID, and category.

## Suggested production values

```env
METRICS_ENABLED=true
METRICS_EXCLUDE_HEALTH_CHECKS=true
SLOW_REQUEST_THRESHOLD_MS=3000
```

## Verification

```powershell
curl.exe -i http://localhost:8000/metrics
curl.exe -i http://localhost:8000/api/v1/health/ready
```

Run a report extraction or chat request, then call `/metrics` again and confirm the relevant counters increase.
