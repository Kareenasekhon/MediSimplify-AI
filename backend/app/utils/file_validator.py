import os
import re
import mimetypes
from typing import Tuple
from fastapi import UploadFile
from app.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "jpg", "jpeg", "png", "webp"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/jpeg",
    "image/png",
    "image/webp"
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

def sanitize_filename(filename: str) -> str:
    """
    Sanitize the uploaded filename by removing directory traversal patterns and keeping only
    alphanumeric characters, spaces, dashes, underscores, and dots.
    """
    # Remove path components
    basename = os.path.basename(filename)
    # Remove anything that isn't alphanumeric, space, dot, dash, or underscore
    sanitized = re.sub(r'[^a-zA-Z0-9._\s-]', '', basename)
    # Collapse multiple spaces or dots
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    return sanitized if sanitized else "uploaded_file"

def validate_uploaded_file(file: UploadFile) -> Tuple[str, str]:
    """
    Validates extension, MIME type, size, and returns sanitized filename and extension.
    Raises ValidationError if validation fails.
    """
    if not file.filename:
        raise ValidationError("Upload failed: No file was uploaded.")

    sanitized_name = sanitize_filename(file.filename)
    _, ext = os.path.splitext(sanitized_name.lower())
    ext = ext.lstrip(".")

    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file format '{ext}'. Supported formats: PDF, DOCX, TXT, JPG, JPEG, PNG, WEBP."
        )

    # Guess MIME type if upload MIME type is generic/missing
    content_type = file.content_type
    if not content_type or content_type == "application/octet-stream":
        content_type, _ = mimetypes.guess_type(sanitized_name)

    if not content_type or content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"Unsupported or invalid MIME type '{content_type}' for extension '.{ext}'."
        )

    return sanitized_name, ext

def check_file_size(file_path: str) -> None:
    """
    Checks if a local file exceeds the max size limits.
    Raises ValidationError if limits are exceeded or file is empty.
    """
    if not os.path.exists(file_path):
        raise ValidationError("Uploaded file not found on disk.")
        
    size = os.path.getsize(file_path)
    if size == 0:
        raise ValidationError("Uploaded file is empty (0 bytes).")
    if size > MAX_FILE_SIZE:
        raise ValidationError(f"File size exceeds the limit of {MAX_FILE_SIZE / (1024 * 1024):.1f} MB.")
