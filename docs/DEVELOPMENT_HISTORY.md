# MediSimplify AI — Development History
> Consolidated from the phase-specific implementation notes retained during development.

---

## Source: `APPLY_FIX.txt`

Phase 5 multilingual schema fix

Copy the backend folder from this package into the root of your existing
MediSimplify-AI repository and choose Replace when Windows asks.

Then run:
  cd backend
  python -m pytest

This fix:
- keeps JSON keys in English for Hindi and Punjabi output
- translates only human-readable values
- adds one automatic repair request when the first JSON response fails validation
- adds multilingual schema tests

---

## Source: `APPLY_PROVIDER_FIX.md`

# Phase 6 Provider Fix

Copy these files into the root of your existing MediSimplify AI repository and replace files when prompted.

## Fixes included

- Accepts valid JSON wrapped in Markdown or surrounded by short explanatory text.
- Keeps strict rejection for genuinely truncated or invalid JSON.
- Increases Phase 5 structured medical explanation output limit from 4096 to 8192 tokens.
- Disables Ollama fallback unless `OLLAMA_ENABLED=true` is explicitly configured.
- Adds parser regression tests.

## Environment setting

Keep this in `backend/.env` when Ollama is not installed/running:

```env
OLLAMA_ENABLED=false
```

To use Ollama later:

```env
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

## Test

From `backend`:

```powershell
python -m pytest -q
```

Expected result for this patched project: `39 passed`.

---

## Source: `PHASE_6_CHANGELOG.md`

# Phase 6 — Conversational RAG

## Added

- Report chunking with configurable overlap
- Lazy Hugging Face sentence-transformer embedding service
- FAISS inner-product vector index with NumPy fallback
- Report-scoped knowledge-base lifecycle
- Top-k retriever with duplicate removal and source chunk IDs
- Report-scoped short-term conversation memory
- Multilingual grounded report Q&A through the existing provider layer
- Chat, status, build/rebuild, clear-history, and delete-index APIs
- Streamlit chat UI with source excerpts and knowledge-base controls
- Phase 5 and Phase 6 README documentation
- RAG service, vector store, and API tests

## Verified

```text
36 passed
```

## Git branch suggestion

```bash
git checkout -b phase-6-rag-chat
git add .
git commit -m "Complete Phase 6: Conversational RAG and report Q&A"
git push -u origin phase-6-rag-chat
```

---

## Source: `PHASE_7_CHANGELOG.md`

# Phase 7 — Intelligent Medical Assistant

## Added

- Automatic routing between report-grounded, general educational, and hybrid answers.
- Manual answer-mode override: Auto, Report Only, General Education, or Hybrid.
- Grandma Mode for gentle, short, everyday-language explanations.
- Report-type-aware suggested questions.
- Response metadata showing the mode and explanation style used.
- General medical education answers that do not require FAISS retrieval.
- Safety separation between general knowledge and patient-specific conclusions.

## API changes

`POST /api/v1/chat` accepts two new optional fields:

```json
{
  "mode": "auto",
  "explanation_style": "standard"
}
```

Allowed modes: `auto`, `report`, `educational`, `hybrid`.

Allowed styles: `standard`, `grandma`.

New endpoint:

```text
GET /api/v1/chat/{report_id}/suggested-questions
```

## Validation

```text
42 passed
```

---

## Source: `PHASE_7_OCR_RESILIENCE_CHANGELOG.md`

# Phase 7 OCR Resilience Patch

This patch removes the Gemini-only dependency from report extraction.

## New flow

- Gemini Vision is attempted first for images and scanned PDFs.
- If Gemini is unavailable or quota-limited, Tesseract performs local OCR.
- Groq or Ollama converts the OCR text into the existing `ExtractionResult` schema.
- Text-based documents now use the shared multi-provider service instead of Gemini directly.

## Added

- `backend/app/services/local_ocr_service.py`
- Tesseract image preprocessing
- Scanned-PDF page rendering through PyMuPDF
- OCR page and DPI limits
- Configurable OCR structuring provider
- Ollama and Tesseract setup guide
- Local OCR fallback tests

## Test result

```text
44 passed
```

The project README remains unchanged as requested.

---

## Source: `PHASE_8_CHANGELOG.md`

# Phase 8 — Multilingual Voice Assistant

## Added
- Browser microphone recording through Streamlit `st.audio_input`.
- Local speech-to-text using `faster-whisper`.
- English, Hindi, and Punjabi transcription hints.
- Text-to-speech responses using gTTS.
- Optional slower speech when Grandma Mode is enabled.
- Voice capability status, transcription, and speech API endpoints.
- Voice API client methods and automated endpoint tests.

## API endpoints
- `GET /api/v1/voice/status`
- `POST /api/v1/voice/transcribe`
- `POST /api/v1/voice/speak`

The main README remains unchanged until Phase 10.

---

## Source: `PHASE_8_SETUP.md`

# Phase 8 Setup

1. Install backend dependencies:
   `pip install -r backend/requirements.txt`
2. Install frontend dependencies:
   `pip install -r frontend/requirements.txt`
3. Keep the default CPU configuration in `backend/.env`:
   `VOICE_WHISPER_MODEL=small`
   `VOICE_WHISPER_DEVICE=cpu`
   `VOICE_WHISPER_COMPUTE_TYPE=int8`
4. The first transcription downloads the selected Whisper model and can take longer.
5. Start FastAPI and Streamlit normally.

For a lower-memory computer, use `VOICE_WHISPER_MODEL=base`. For higher accuracy, use `medium` if the computer has enough RAM.

---

## Source: `PHASE_9_5_BATCH_2_CHANGELOG.md`

# Phase 9.5 Batch 2 — Health Analytics Dashboard

## Added
- Interactive visual summary gauge
- Finding-status donut chart
- Quick analytics metric cards
- Findings-needing-attention panel
- Optional normalized reference-range chart
- Clear non-diagnostic safety messaging

## Changed
- Integrated analytics after parameter cards and before recommendations
- Added Plotly to frontend requirements
- Added responsive light/dark analytics styling

## Safety
The visual score is only the percentage of classified items labelled within range. It is not a health score, diagnosis, urgency assessment, prognosis, or comparison of medical importance.

---

## Source: `PHASE_9_5_BATCH_3_CHANGELOG.md`

# Phase 9.5 Batch 3 — Report History

- Stores structured analysis and metadata locally in `frontend/data/report_history.json`.
- Never stores original uploaded report bytes.
- Auto-saves completed analyses with upsert behavior.
- Adds search and report-type filters.
- Adds open-preview, PDF redownload, delete, and clear-history actions.
- Saved previews do not recreate the original RAG knowledge base.

---

## Source: `PHASE_9_5_BATCH_4_CHANGELOG.md`

# Phase 9.5 Batch 4 — Final UX Polish

- Added reusable process-step, empty-state, error-state and one-time toast components.
- Added friendly offline-backend presentation.
- Added extraction progress steps and completion toasts.
- Added analysis-ready and history-saved feedback.
- Added focus states, reduced-motion support, micro-animations and responsive cleanup.
- No backend or dependency changes.

---

## Source: `OLLAMA_AND_LOCAL_OCR_SETUP.md`

# Ollama and Local OCR Setup

## 1. Install Tesseract OCR on Windows

Install the Windows Tesseract application. Then locate:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Add this to `backend/.env`:

```env
LOCAL_OCR_ENABLED=true
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
TESSERACT_LANGUAGES=eng
OCR_STRUCTURING_PROVIDER=groq
```

Punjabi/Hindi OCR requires the relevant Tesseract language files. Example:

```env
TESSERACT_LANGUAGES=eng+hin+pan
```

## 2. Install and start Ollama

Install Ollama, then open PowerShell:

```powershell
ollama --version
ollama pull llama3.2:3b
ollama run llama3.2:3b
```

Exit the interactive model with `/bye`.

Normally the Ollama desktop application starts the local server automatically. Verify it:

```powershell
curl http://localhost:11434/api/tags
```

## 3. Enable Ollama in backend/.env

```env
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
LLM_FALLBACK_PROVIDERS=groq,ollama
```

To use Ollama for structuring local OCR text:

```env
OCR_STRUCTURING_PROVIDER=ollama
```

For faster development, keep `OCR_STRUCTURING_PROVIDER=groq` and use Ollama as the final fallback.

## 4. Install Python dependencies

From the backend folder:

```powershell
pip install -r requirements.txt
```

## 5. Restart FastAPI

```powershell
uvicorn app.main:app --reload
```

## Resulting extraction flow

```text
Image or scanned PDF
    -> Gemini Vision
    -> on quota/service failure: Tesseract OCR
    -> Groq or Ollama converts OCR text to structured JSON
```
