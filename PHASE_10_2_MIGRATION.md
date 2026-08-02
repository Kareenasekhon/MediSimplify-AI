# Phase 10.2 — Production Configuration Migration

## New variables

- `APP_ENV`: `development`, `testing`, `docker`, or `production`
- `DEBUG`
- `API_DOCS_ENABLED`
- `ALLOWED_ORIGINS`: comma-separated frontend origins
- `ALLOW_CREDENTIALS`
- `MAX_REPORT_SIZE_MB`
- `MAX_QUESTION_LENGTH`
- `TEMPORARY_DATA_DIR`
- Frontend: `BACKEND_REQUEST_TIMEOUT_SECONDS`, `BACKEND_CONNECT_TIMEOUT_SECONDS`

## Existing installations

Your current `backend/.env` remains valid. Add `APP_ENV=development` locally. Docker Compose overrides it with `APP_ENV=docker`.

Production startup rejects wildcard CORS, debug mode, and a configuration with no LLM provider. Optional local services still produce warnings rather than preventing startup.
