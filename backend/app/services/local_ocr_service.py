"""Local OCR fallback for report images and scanned PDFs.

Tesseract performs transcription only. The extracted text is later structured by
MediSimplify's provider abstraction (Groq, Gemini, or Ollama).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.exceptions import ProviderError

logger = logging.getLogger("medisimplify")


def _load_pytesseract() -> Any:
    try:
        import pytesseract
    except ImportError as exc:
        raise ProviderError(
            "Local OCR is unavailable because pytesseract is not installed. "
            "Install backend requirements and the Tesseract desktop application."
        ) from exc
    return pytesseract


def _configure_tesseract(pytesseract: Any) -> None:
    configured_path = settings.tesseract_cmd.strip()
    if configured_path:
        if not Path(configured_path).exists():
            raise ProviderError(
                f"Configured Tesseract executable was not found: {configured_path}"
            )
        pytesseract.pytesseract.tesseract_cmd = configured_path
        return

    if shutil.which("tesseract") is None:
        raise ProviderError(
            "Tesseract OCR is not installed or is not on PATH. On Windows, install "
            "Tesseract and set TESSERACT_CMD in backend/.env."
        )


def _ocr_pil_image(image: Any, page_number: int = 1) -> str:
    pytesseract = _load_pytesseract()
    _configure_tesseract(pytesseract)

    try:
        text = pytesseract.image_to_string(
            image,
            lang=settings.tesseract_languages,
            config=settings.tesseract_config,
        )
    except Exception as exc:
        logger.error("Local OCR failed on page %s", page_number, exc_info=True)
        raise ProviderError(f"Local OCR failed on page {page_number}: {exc}") from exc

    normalized = "\n".join(
        " ".join(line.split()) for line in text.splitlines() if line.strip()
    ).strip()
    return normalized


def extract_text_from_image(file_path: str) -> str:
    """Transcribe one image using the local Tesseract engine."""
    try:
        from PIL import Image, ImageEnhance, ImageOps
    except ImportError as exc:
        raise ProviderError("Pillow is required for local image OCR.") from exc

    try:
        with Image.open(file_path) as source:
            image = ImageOps.exif_transpose(source).convert("L")
            image = ImageOps.autocontrast(image)
            image = ImageEnhance.Sharpness(image).enhance(1.4)
            text = _ocr_pil_image(image)
    except ProviderError:
        raise
    except Exception as exc:
        raise ProviderError(f"The image could not be prepared for local OCR: {exc}") from exc

    if not text:
        raise ProviderError("Local OCR could not detect readable text in the image.")
    return text


def extract_text_from_scanned_pdf(file_path: str) -> str:
    """Render scanned PDF pages and transcribe them with Tesseract."""
    try:
        import fitz  # PyMuPDF
        from PIL import Image
    except ImportError as exc:
        raise ProviderError(
            "PyMuPDF and Pillow are required for scanned-PDF OCR."
        ) from exc

    page_texts: list[str] = []
    document = None
    try:
        document = fitz.open(file_path)
        if document.page_count > settings.ocr_max_pdf_pages:
            raise ProviderError(
                f"The scanned PDF has {document.page_count} pages. Local OCR supports "
                f"up to {settings.ocr_max_pdf_pages} pages per upload."
            )

        zoom = settings.ocr_pdf_dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            text = _ocr_pil_image(image, page_number=page_index + 1)
            if text:
                page_texts.append(f"[Page {page_index + 1}]\n{text}")
    except ProviderError:
        raise
    except Exception as exc:
        logger.error("Local scanned-PDF OCR failed", exc_info=True)
        raise ProviderError(f"Local scanned-PDF OCR failed: {exc}") from exc
    finally:
        try:
            document.close()
        except Exception:
            pass

    combined = "\n\n".join(page_texts).strip()
    if not combined:
        raise ProviderError("Local OCR could not detect readable text in the scanned PDF.")
    return combined
