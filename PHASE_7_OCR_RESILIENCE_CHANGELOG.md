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
