from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, File, UploadFile, status

from app.core.exceptions import ExtractionError, ResourceNotFoundError, ValidationError
from app.models.extraction_models import ExtractionConfirmRequest, ReportExtractionResponse
from app.services import (
    document_service,
    image_validation_service,
    multimodal_service,
    session_service,
)
from app.utils.file_validator import (
    check_file_size,
    validate_file_signature,
    validate_identifier,
    validate_uploaded_file,
)
from app.utils.temporary_files import delete_temporary_file, save_temporary_file

router = APIRouter(tags=["Extraction"])
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


@router.post(
    "/reports/extract",
    response_model=ReportExtractionResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_report(file: UploadFile = File(...)) -> ReportExtractionResponse:
    """Validate, extract, structure, and stage one report for user review."""
    _, extension = validate_uploaded_file(file)
    temporary_path = save_temporary_file(file, extension)

    try:
        check_file_size(temporary_path)
        validate_file_signature(temporary_path, extension)
        report_id = Path(temporary_path).stem
        warnings: list[str] = []
        is_scanned_pdf = False

        if extension in IMAGE_EXTENSIONS:
            quality = image_validation_service.check_image_quality(temporary_path)
            warnings.extend(quality.get("issues", []))
            if not quality.get("can_continue", False):
                raise ValidationError(
                    "Image quality is too poor for safe extraction. "
                    + " ".join(warnings)
                )

            mime_type = file.content_type or (
                "image/jpeg" if extension in {"jpg", "jpeg"} else f"image/{extension}"
            )
            structured_data = await multimodal_service.extract_structured_from_image(
                temporary_path,
                mime_type,
            )
            input_type = "image"

        elif extension == "pdf":
            is_scanned_pdf = document_service.is_scanned_or_image_only_pdf(
                temporary_path
            )
            if is_scanned_pdf:
                structured_data = await multimodal_service.extract_structured_from_pdf(
                    temporary_path
                )
                warnings.append(
                    "The PDF appears scanned, so multimodal extraction was used."
                )
                input_type = "image"
            else:
                raw_text = document_service.extract_document_text(
                    temporary_path, extension
                )
                raw_text = _normalize_extracted_text(raw_text)
                structured_data = await multimodal_service.extract_structured_from_text(
                    raw_text
                )
                input_type = "document"

        else:
            raw_text = document_service.extract_document_text(
                temporary_path, extension
            )
            raw_text = _normalize_extracted_text(raw_text)
            structured_data = await multimodal_service.extract_structured_from_text(
                raw_text
            )
            input_type = "document"

        extracted_text = structured_data.extracted_text.strip()
        if not extracted_text:
            raise ExtractionError(
                "No readable report text could be extracted from the uploaded file."
            )

        session_payload: Dict[str, Any] = {
            "report_id": report_id,
            "input_type": input_type,
            "raw_text": extracted_text,
            "structured_data": structured_data.model_dump(),
            "quality_warnings": warnings,
            "unreadable_text": structured_data.unreadable_text,
            "confirmed": False,
        }
        session_service.create_session(report_id, session_payload)

        return ReportExtractionResponse(
            report_id=report_id,
            input_type=input_type,
            extracted_text=extracted_text,
            structured_data=structured_data,
            quality_warnings=warnings,
            unreadable_text=structured_data.unreadable_text,
            requires_confirmation=True,
        )
    finally:
        delete_temporary_file(temporary_path)


@router.post(
    "/reports/{report_id}/confirm-analysis",
    status_code=status.HTTP_200_OK,
)
async def confirm_report_analysis(
    report_id: str,
    request: ExtractionConfirmRequest,
) -> Dict[str, str]:
    """Store user-reviewed extraction content for the next project phase."""
    report_id = validate_identifier(report_id, "report ID")
    session = session_service.get_session(report_id)
    if not session:
        raise ResourceNotFoundError(
            "Active report session was not found. Please upload the report again."
        )

    confirmed_text = request.confirmed_text.strip()
    if not confirmed_text:
        raise ValidationError("Confirmed report text cannot be empty.")

    session_service.update_session(
        report_id,
        {
            "raw_text": confirmed_text,
            "structured_data": request.corrected_structured_data,
            "language": request.language,
            "provider": request.provider,
            "confirmed": True,
        },
    )

    return {
        "status": "success",
        "report_id": report_id,
        "message": "Report extraction confirmed and saved.",
    }


def _normalize_extracted_text(raw_text: str) -> str:
    """Remove excessive blank space while preserving line boundaries."""
    normalized_lines = [" ".join(line.split()) for line in raw_text.splitlines()]
    normalized = "\n".join(line for line in normalized_lines if line)
    if not normalized.strip():
        raise ExtractionError("The uploaded document contains no readable text.")
    return normalized
