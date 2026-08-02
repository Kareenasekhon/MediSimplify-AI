from __future__ import annotations

import io
import os
import tempfile
from functools import lru_cache

from app.core.config import settings
from app.core.exceptions import ProviderError

LANGUAGE_CODES = {
    "english": "en",
    "hindi": "hi",
    "punjabi": "pa",
}


@lru_cache(maxsize=1)
def _load_whisper_model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ProviderError(
            "Voice transcription requires faster-whisper. Run: pip install faster-whisper"
        ) from exc

    kwargs = {
        "device": settings.voice_whisper_device,
        "compute_type": settings.voice_whisper_compute_type,
        "num_workers": settings.whisper_num_workers,
    }
    if settings.whisper_cpu_threads > 0:
        kwargs["cpu_threads"] = settings.whisper_cpu_threads
    return WhisperModel(settings.voice_whisper_model, **kwargs)


def get_status() -> dict:
    transcription_enabled = settings.voice_transcription_enabled
    speech_enabled = settings.voice_speech_enabled
    return {
        "transcription_enabled": transcription_enabled,
        "speech_enabled": speech_enabled,
        "transcription_model": settings.voice_whisper_model,
        "detail": (
            "Voice input and output are enabled."
            if transcription_enabled and speech_enabled
            else "One or more voice features are disabled in configuration."
        ),
    }


def transcribe_audio(content: bytes, filename: str, language: str | None = None) -> dict:
    if not settings.voice_transcription_enabled:
        raise ProviderError("Voice transcription is disabled.")
    if not content:
        raise ProviderError("The recorded audio is empty.")
    if len(content) > settings.voice_max_audio_mb * 1024 * 1024:
        raise ProviderError(
            f"Audio exceeds the {settings.voice_max_audio_mb} MB limit."
        )

    suffix = os.path.splitext(filename or "voice.wav")[1] or ".wav"
    model = _load_whisper_model()
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        code = LANGUAGE_CODES.get((language or "").lower())
        segments, info = model.transcribe(
    temp_path,
    language=code,
    beam_size=settings.voice_beam_size,
    vad_filter=True,
    vad_parameters=dict(
        min_silence_duration_ms=300,
    ),
    condition_on_previous_text=False,
    word_timestamps=False,
)
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
        if not text:
            raise ProviderError("No clear speech was detected. Please record again.")

        return {
            "text": text,
            "language": getattr(info, "language", code or "unknown"),
            "duration_seconds": getattr(info, "duration", None),
            "model": settings.voice_whisper_model,
        }
    except ProviderError:
        raise
    except Exception as exc:
        raise ProviderError(f"Voice transcription failed: {exc}") from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def synthesize_speech(text: str, language: str, slow: bool = False) -> bytes:
    if not settings.voice_speech_enabled:
        raise ProviderError("Voice output is disabled.")
    try:
        from gtts import gTTS
    except ImportError as exc:
        raise ProviderError("Voice output requires gTTS. Run: pip install gTTS") from exc

    language_code = LANGUAGE_CODES.get(language.lower(), "en")
    output = io.BytesIO()
    try:
        gTTS(text=text, lang=language_code, slow=slow).write_to_fp(output)
        return output.getvalue()
    except Exception as exc:
        raise ProviderError(f"Speech generation failed: {exc}") from exc
