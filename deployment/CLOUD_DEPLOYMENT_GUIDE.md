# MediSimplify AI — Cloud Deployment Guide

## Architecture
Deploy two Docker web services from this monorepo:

1. **Backend:** `backend/Dockerfile`, FastAPI, health check `/api/v1/health/ready`.
2. **Frontend:** `frontend/Dockerfile`, Streamlit, health check `/_stcore/health`.

Both startup scripts read the platform-provided `PORT` variable. Local Docker Compose remains unchanged.

## Resource warning
The backend includes Tesseract, FAISS, sentence-transformers, PyTorch, and faster-whisper. A small/free instance can run out of memory or disk. For the first cloud demo, disable local Whisper with `VOICE_TRANSCRIPTION_ENABLED=false`. Use Groq/Gemini for model requests. Ollama is not suitable inside these hosted services unless deployed separately.

## Render
1. Push this branch to GitHub.
2. In Render, create a **Blueprint** and select the repository. Render reads `render.yaml`.
3. During initial Blueprint creation, enter values for variables marked `sync: false`:
   - `ALLOWED_ORIGINS` — the final Streamlit URL.
   - `GROQ_API_KEY` and/or `GEMINI_API_KEY`.
4. The Blueprint uses paid Starter services because persistent disks are attached. Adjust plans and disk sizes in `render.yaml` when needed.
5. After both services are live, confirm:
   - backend `/api/v1/health/ready` returns 200;
   - frontend `/_stcore/health` returns 200;
   - upload, OCR, analysis, history, and PDF export work.

The frontend uses Render's private backend `hostport`, so the server-to-server connection does not depend on the public backend URL.

## Railway
Create two Railway services from the same GitHub repository.

### Backend service
- Root directory: `/backend`
- Config file path: `/deployment/railway/backend.railway.json`
- Attach a volume mounted at `/var/data`
- Add the backend variables from `.env.railway.example`
- Enable public networking and note the generated backend URL

### Frontend service
- Root directory: `/frontend`
- Config file path: `/deployment/railway/frontend.railway.json`
- Attach a volume mounted at `/var/data`
- Set `BACKEND_API_URL` to the backend's Railway public URL
- Enable public networking

Railway injects `PORT`; the cloud start scripts bind to it automatically.

## Persistent data
- Backend temporary/model cache: under `PERSISTENT_DATA_DIR` (`/var/data` in examples).
- Frontend report history: `REPORT_HISTORY_PATH=/var/data/report_history.json`.
- Original uploaded report bytes are not retained in history.

## Production checklist
- Never commit `.env` files containing real keys.
- Set `APP_ENV=production`, `DEBUG=false`, and a precise `ALLOWED_ORIGINS` value.
- Keep API docs disabled unless they are intentionally public.
- Start with one backend replica because the in-memory rate limiter and report-scoped runtime state are process-local.
- Use an external database/Redis before horizontal scaling.
