from __future__ import annotations

import mimetypes
import os
import re
import zipfile
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "jpg", "jpeg", "png", "webp"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/jpeg",
    "image/png",
    "image/webp",
}
MAX_FILE_SIZE = settings.max_report_size_mb * 1024 * 1024
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")


def sanitize_filename(filename: str) -> str:
    """Return a traversal-safe display filename."""
    basename = os.path.basename(filename or "")
    sanitized = re.sub(r"[^a-zA-Z0-9._\s-]", "", basename)
    sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
    return sanitized or "uploaded_file"


def validate_identifier(value: str, field_name: str = "identifier") -> str:
    normalized = str(value or "").strip()
    if not _IDENTIFIER_RE.fullmatch(normalized):
        raise ValidationError(f"Invalid {field_name}.")
    return normalized


def validate_uploaded_file(file: UploadFile) -> Tuple[str, str]:
    """Validate filename extension and declared MIME type."""
    if not file.filename:
        raise ValidationError("Upload failed: No file was uploaded.")

    sanitized_name = sanitize_filename(file.filename)
    extension = Path(sanitized_name).suffix.lower().lstrip(".")
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file format '{extension}'. Supported formats: "
            "PDF, DOCX, TXT, JPG, JPEG, PNG, WEBP."
        )

    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if not content_type or content_type == "application/octet-stream":
        content_type, _ = mimetypes.guess_type(sanitized_name)
    if not content_type or content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"Unsupported or invalid MIME type '{content_type}' for extension '.{extension}'."
        )
    return sanitized_name, extension


def check_file_size(file_path: str) -> None:
    """Reject missing, empty, or oversized report files."""
    if not os.path.exists(file_path):
        raise ValidationError("Uploaded file not found on disk.")
    size = os.path.getsize(file_path)
    if size == 0:
        raise ValidationError("Uploaded file is empty (0 bytes).")
    if size > MAX_FILE_SIZE:
        raise ValidationError(
            f"File size exceeds the limit of {settings.max_report_size_mb} MB."
        )


def validate_file_signature(file_path: str, extension: str) -> None:
    """Verify common file signatures so renamed executables are rejected."""
    path = Path(file_path)
    with path.open("rb") as handle:
        header = handle.read(16)

    valid = True
    if extension == "pdf":
        valid = header.startswith(b"%PDF-")
    elif extension in {"jpg", "jpeg"}:
        valid = header.startswith(b"\xff\xd8\xff")
    elif extension == "png":
        valid = header.startswith(b"\x89PNG\r\n\x1a\n")
    elif extension == "webp":
        valid = header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    elif extension == "docx":
        valid = zipfile.is_zipfile(path)
        if valid:
            try:
                with zipfile.ZipFile(path) as archive:
                    names = set(archive.namelist())
                valid = "[Content_Types].xml" in names and any(
                    name.startswith("word/") for name in names
                )
            except (OSError, zipfile.BadZipFile):
                valid = False
    elif extension == "txt":
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                valid = False

    if not valid:
        raise ValidationError(
            f"The uploaded file contents do not match the '.{extension}' format."
        )


def validate_audio_upload(content: bytes, filename: str, content_type: str | None) -> str:
    """Validate voice-upload size, extension, and coarse MIME type."""
    if not content:
        raise ValidationError("The recorded audio is empty.")
    if len(content) > settings.voice_max_audio_mb * 1024 * 1024:
        raise ValidationError(
            f"Audio exceeds the {settings.voice_max_audio_mb} MB limit."
        )
    safe_name = sanitize_filename(filename or "voice.wav")
    extension = Path(safe_name).suffix.lower().lstrip(".")
    if extension not in settings.audio_extensions:
        raise ValidationError(
            "Unsupported audio format. Allowed formats: "
            + ", ".join(sorted(settings.audio_extensions)).upper()
            + "."
        )
    mime = (content_type or "").split(";", 1)[0].strip().lower()
    if mime and mime != "application/octet-stream" and not mime.startswith("audio/"):
        raise ValidationError(f"Unsupported audio MIME type '{mime}'.")
    return safe_name
