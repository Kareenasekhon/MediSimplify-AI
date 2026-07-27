# MediSimplify AI

MediSimplify AI is a multilingual, multimodal, and voice-enabled medical report explanation platform. It helps users understand written findings of medical reports (such as blood laboratory results, radiology report texts, and prescriptions) in simple, everyday language.

## 1. Project Features (Planned)
* **Multilingual Explanations**: English, Hindi (Devanagari script), and Punjabi (Gurmukhi script).
* **Multimodal Extraction**: Upload PDF/DOCX/TXT files or images (JPEG, PNG, WEBP), or capture reports via device camera.
* **Extraction Verification**: Review and correct extracted terms, decimal values, units, and drug names before analysis.
* **Agent-Based Routing**: Auto-classify reports (Supervisor Agent) and process them using specialized agents (Blood Report, Prescription, Radiology, or Fallback Agents).
* **Retrieval-Augmented Generation (RAG)**: Ground follow-up questions directly in the report context via session-specific FAISS indexing.
* **Grandma Mode**: Highly simplified explanations suitable for elderly users.
* **Voice-Enabled**: Speech-to-text input and text-to-speech output.
* **Doctor Visit Pack**: Downloadable PDF summaries, ZIP packages, audio MP3s, and question lists for doctor consultation.

---

## 2. Phase 1: Project Foundation
This phase establishes the baseline codebase:
* **Backend**: FastAPI web server with custom Pydantic settings loading, structured error handler, secure logging, custom exceptions, and health endpoints.
* **Frontend**: Streamlit client dashboard displaying backend connectivity status, UI layout structure, and initial navigation components.
* **Testing**: Automated backend testing suite using `pytest`.

---

## 3. Setup and Execution

### Prerequisites
* Python 3.10 or higher installed.

### Backend Setup
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy environment variables file:
   ```bash
   copy .env.example .env
   ```
5. Run tests:
   ```bash
   pytest
   ```
6. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend Setup
1. Navigate to the `frontend/` directory:
   ```bash
   cd ../frontend
   ```
2. Create and activate a virtual environment (optional, or use a shared one):
   ```bash
   python -m venv venv
   # Activate it
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the Streamlit application:
   ```bash
   streamlit run Home.py
   ```

## 4. Phase 2: Report Upload and OCR

Phase 2 adds the report-ingestion workflow:

- Upload PDF, DOCX, TXT, JPG, JPEG, PNG, and WEBP reports.
- Validate file extension, MIME type, size, and empty uploads.
- Extract text from digital PDF, DOCX, and TXT documents.
- Detect scanned PDFs and route them to Gemini multimodal extraction.
- Check image resolution, brightness, contrast, blur, and orientation.
- Return Pydantic-validated structured medical data.
- Review and edit extracted report text before confirmation.
- Store confirmed extraction data in the active in-memory report session.

### Phase 2 API

- `POST /api/v1/reports/extract`
- `POST /api/v1/reports/{report_id}/confirm-analysis`

Gemini calls require `GEMINI_API_KEY` in `backend/.env`. Automated tests mock provider calls and do not consume API quota.

## Phase 3 — LLM Provider Layer

Phase 3 adds a provider-independent text generation foundation for later medical agents.

Implemented:

- Common `BaseLLMProvider` interface
- Gemini text provider
- Groq text provider
- Ollama local provider
- Provider factory
- Configurable default and fallback order
- Timeout and retry handling
- JSON parsing and Pydantic-ready structured validation helper
- Provider configuration status endpoint
- Explicit provider connection-test endpoint
- Streamlit provider status and test control
- Mocked backend tests that do not consume API credits

Provider endpoints:

- `GET /api/v1/providers/status`
- `POST /api/v1/providers/test`

The live test endpoint sends one small request and may consume provider credits. Normal automated tests mock provider calls.

## Phase 4 — Supervisor Agent and Report Routing

Phase 4 adds safe report-type routing after extraction confirmation. Deterministic keyword scoring handles clear blood, prescription, and written-radiology reports without consuming LLM credits. The Supervisor Agent uses the Phase 3 provider layer only for uncertain text, and low-confidence or mixed results require manual confirmation.

New endpoints:

- `POST /api/v1/analysis/route`
- `POST /api/v1/analysis/{report_id}/manual-route`

This phase performs classification only. It does not diagnose, interpret medical values, or implement the specialised agents.
