import os

import docx
from pypdf import PdfReader

from app.core.config import settings
from app.core.exceptions import ExtractionError


def extract_text_from_txt(file_path: str) -> str:
    """Read a plain-text report using UTF-8 with a Latin-1 fallback."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="latin-1") as file:
                return file.read()
        except Exception as exc:
            raise ExtractionError(f"Failed to read text file with Latin-1 fallback: {exc}") from exc
    except Exception as exc:
        raise ExtractionError(f"Failed to read plain text file: {exc}") from exc


def extract_text_from_docx(file_path: str) -> str:
    """Extract non-empty paragraphs from a digital DOCX document."""
    try:
        document = docx.Document(file_path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
    except Exception as exc:
        raise ExtractionError(f"Failed to extract text from DOCX file: {exc}") from exc


def _pdf_reader(file_path: str) -> PdfReader:
    reader = PdfReader(file_path)
    if reader.is_encrypted:
        raise ExtractionError(
            "The PDF report is password-protected and cannot be processed. "
            "Please remove the password and try again."
        )
    if len(reader.pages) > settings.document_max_pdf_pages:
        raise ExtractionError(
            f"The PDF contains {len(reader.pages)} pages. The current limit is "
            f"{settings.document_max_pdf_pages} pages."
        )
    return reader


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a bounded, non-encrypted digital PDF."""
    try:
        reader = _pdf_reader(file_path)
        return "\n".join(text for page in reader.pages if (text := page.extract_text()))
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError(f"Failed to extract text from PDF file: {exc}") from exc


def is_scanned_or_image_only_pdf(file_path: str) -> bool:
    """Detect likely scanned PDFs using an early-exit text-density check."""
    try:
        reader = _pdf_reader(file_path)
        extracted_char_count = 0
        # A few pages are enough for the scanned/digital classification and avoid
        # parsing an entire long report twice.
        sample_pages = min(len(reader.pages), 5)
        for page in reader.pages[:sample_pages]:
            text = page.extract_text()
            if text:
                extracted_char_count += len(text.strip())
                if extracted_char_count >= 150:
                    return False
        return extracted_char_count < 150 and os.path.getsize(file_path) > 15 * 1024
    except ExtractionError:
        raise
    except Exception:
        return False


def extract_document_text(file_path: str, ext: str) -> str:
    """Route extraction according to the validated file extension."""
    if ext == "txt":
        return extract_text_from_txt(file_path)
    if ext == "docx":
        return extract_text_from_docx(file_path)
    if ext == "pdf":
        return extract_text_from_pdf(file_path)
    raise ExtractionError(f"Unsupported document extension: .{ext}")
