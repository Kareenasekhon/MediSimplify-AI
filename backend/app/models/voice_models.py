from pydantic import BaseModel, Field

from app.models.analysis_models import AnalysisLanguage


class VoiceStatusResponse(BaseModel):
    transcription_enabled: bool
    speech_enabled: bool
    transcription_model: str
    detail: str


class TranscriptionResponse(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: str
    duration_seconds: float | None = None
    model: str


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    language: AnalysisLanguage = AnalysisLanguage.ENGLISH
    slow: bool = False
