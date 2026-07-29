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
