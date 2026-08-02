from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.responses import Response

from app.models.voice_models import SpeechRequest, TranscriptionResponse, VoiceStatusResponse
from app.services import voice_service
from app.utils.file_validator import validate_audio_upload

router = APIRouter(prefix="/voice", tags=["Voice Assistant"])


@router.get("/status", response_model=VoiceStatusResponse)
async def voice_status() -> VoiceStatusResponse:
    return VoiceStatusResponse(**voice_service.get_status())


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
)
async def transcribe_voice(
    audio: UploadFile = File(...),
    language: str | None = Form(default=None),
) -> TranscriptionResponse:
    content = await audio.read()
    safe_name = validate_audio_upload(
        content, audio.filename or "voice.wav", audio.content_type
    )
    result = voice_service.transcribe_audio(content, safe_name, language)
    return TranscriptionResponse(**result)


@router.post("/speak", response_class=Response)
async def speak_response(request: SpeechRequest) -> Response:
    audio = voice_service.synthesize_speech(
        request.text,
        request.language.value,
        request.slow,
    )
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=medisimplify-response.mp3"},
    )
