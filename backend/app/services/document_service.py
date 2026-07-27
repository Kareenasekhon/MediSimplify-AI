import os
from pypdf import PdfReader
import docx
from app.core.exceptions import ExtractionError

def extract_text_from_txt(file_path: str) -> str:
    """
    Reads a plain text file, attempting UTF-8 first, with Latin-1 fallback.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception as exc:
            raise ExtractionError(f"Failed to read text file with Latin-1 fallback: {str(exc)}")
    except Exception as exc:
        raise ExtractionError(f"Failed to read plain text file: {str(exc)}")

def extract_text_from_docx(file_path: str) -> str:
    """
    Extracts text from a digital DOCX document.
    """
    try:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        return "\n".join(full_text)
    except Exception as exc:
        raise ExtractionError(f"Failed to extract text from DOCX file: {str(exc)}")

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extracts text from a digital PDF file. Checks for password protection.
    """
    try:
        reader = PdfReader(file_path)
        if reader.is_encrypted:
            raise ExtractionError(
                "The PDF report is password-protected and cannot be processed. Please remove the password and try again."
            )
            
        full_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
        return "\n".join(full_text)
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError(f"Failed to extract text from PDF file: {str(exc)}")

def is_scanned_or_image_only_pdf(file_path: str) -> bool:
    """
    Determines if a PDF is scanned/image-only by extracting text.
    If length is < 150 characters, but file size > 15 KB, it's flagged as scanned.
    """
    try:
        reader = PdfReader(file_path)
        if reader.is_encrypted:
            return False  # Will fail validation on check
        
        extracted_char_count = 0
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_char_count += len(text.strip())
        
        file_size = os.path.getsize(file_path)
        # Low character density relative to size indicates scanned images inside
        if extracted_char_count < 150 and file_size > 15 * 1024:
            return True
        return False
    except Exception:
        # Fallback to False on parsing error so main routine handles failure
        return False

def extract_document_text(file_path: str, ext: str) -> str:
    """
    Unified extraction router based on file extension.
    """
    if ext == "txt":
        return extract_text_from_txt(file_path)
    elif ext == "docx":
        return extract_text_from_docx(file_path)
    elif ext == "pdf":
        return extract_text_from_pdf(file_path)
    else:
        raise ExtractionError(f"Unsupported document extension: .{ext}")
