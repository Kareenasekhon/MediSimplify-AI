# MediSimplify AI — Docker Setup

## Prerequisites

- Docker Desktop running with Linux containers / WSL 2.
- A configured `backend/.env` file. Copy `backend/.env.example` if needed and add your own API keys.

## Start the application

From the project root:

```powershell
docker compose up --build
```

Open:

- Frontend: http://localhost:8501
- Backend Swagger: http://localhost:8000/docs
- Backend health: http://localhost:8000/api/v1/health

The initial backend build is large because it installs FAISS, sentence-transformers, faster-whisper, OCR dependencies, and related libraries. The first voice or embedding request may also download a model into the persistent `huggingface_cache` volume.

## Run in the background

```powershell
docker compose up --build -d
```

View logs:

```powershell
docker compose logs -f
```

View one service:

```powershell
docker compose logs -f backend
docker compose logs -f frontend
```

## Stop the application

```powershell
docker compose down
```

To also delete Docker volumes and downloaded model caches:

```powershell
docker compose down -v
```

## Rebuild after changing dependencies

```powershell
docker compose build --no-cache
docker compose up
```

## Ollama on Windows host

Keep Ollama running on Windows and set these values in `backend/.env`:

```env
OLLAMA_ENABLED=true
OLLAMA_MODEL=llama3.2:3b
```

`compose.yaml` supplies `OLLAMA_BASE_URL=http://host.docker.internal:11434` automatically.

Verify Ollama on Windows before starting the containers:

```powershell
ollama list
curl.exe http://localhost:11434/api/tags
```

## Local OCR

Tesseract is installed inside the backend image. Docker automatically uses:

```env
TESSERACT_CMD=/usr/bin/tesseract
```

The Windows Tesseract installation is not required by the container.

## Data and privacy

Named Docker volumes preserve:

- frontend report-history JSON data;
- downloaded Hugging Face models;
- backend temporary working directory.

The current FAISS implementation is process-memory based and is rebuilt when necessary; it is not yet persisted as a disk index.

Do not commit `backend/.env`, medical reports, extracted report content, or generated patient files.

## Troubleshooting

Check container state:

```powershell
docker compose ps
```

Validate the Compose file:

```powershell
docker compose config
```

If port 8000 or 8501 is already in use, stop the local Uvicorn/Streamlit process before running Compose.
