from __future__ import annotations

import shutil
from pathlib import Path

from loguru import logger

from app.core.config import settings


def validate_runtime_environment() -> None:
    """Create required directories and log a secret-safe startup summary."""
    for directory in (
        Path(settings.persistent_data_dir),
        Path(settings.temporary_data_dir),
        Path(settings.model_cache_dir or settings.persistent_data_dir / "model_cache"),
    ):
        directory.mkdir(parents=True, exist_ok=True)

    provider_text = ", ".join(settings.configured_providers) or "none configured"
    logger.info(
        "Starting MediSimplify | environment={} | platform={} | debug={} | providers={} | docs={}",
        settings.app_env,
        settings.cloud_platform,
        settings.debug,
        provider_text,
        "enabled" if settings.api_docs_enabled else "disabled",
    )
    logger.info(
        "Runtime storage | persistent={} | temporary={} | model_cache={}",
        settings.persistent_data_dir,
        settings.temporary_data_dir,
        settings.model_cache_dir,
    )
    logger.info(
        "Runtime limits | report={} MB | audio={} MB | question={} chars | CORS origins={}",
        settings.max_report_size_mb,
        settings.voice_max_audio_mb,
        settings.max_question_length,
        settings.cors_origins,
    )
    logger.info(
        "Observability | metrics={} | exclude_health={} | slow_threshold_ms={}",
        "enabled" if settings.metrics_enabled else "disabled",
        settings.metrics_exclude_health_checks,
        settings.slow_request_threshold_ms,
    )

    if not settings.configured_providers:
        logger.warning("No LLM provider is configured; AI operations will be unavailable.")

    if settings.local_ocr_enabled:
        executable = settings.tesseract_cmd or shutil.which("tesseract")
        if executable:
            logger.info("Local OCR enabled; Tesseract executable detected.")
        else:
            logger.warning(
                "Local OCR is enabled but Tesseract was not detected. "
                "Gemini Vision may still be used when configured."
            )

    if settings.voice_transcription_enabled:
        logger.info(
            "Voice transcription enabled | model={} | device={} | compute={}",
            settings.voice_whisper_model,
            settings.voice_whisper_device,
            settings.voice_whisper_compute_type,
        )
