from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Central application configuration loaded from environment variables."""

    app_env: Literal["development", "testing", "docker", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "ENV"),
    )
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_docs_enabled: bool = True
    allowed_origins: str = "http://localhost:8501,http://127.0.0.1:8501"
    allow_credentials: bool = True

    security_headers_enabled: bool = True
    rate_limit_enabled: bool = True
    rate_limit_uploads_per_minute: int = Field(default=5, ge=1, le=120)
    rate_limit_questions_per_minute: int = Field(default=20, ge=1, le=600)
    rate_limit_voice_per_minute: int = Field(default=10, ge=1, le=120)
    trusted_proxy_headers: bool = True

    max_report_size_mb: int = Field(default=5, ge=1, le=100)
    max_question_length: int = Field(default=4000, ge=100, le=20000)
    temporary_data_dir: Path = BASE_DIR / "temporary_data"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    default_llm_provider: Literal["gemini", "groq", "ollama"] = "gemini"
    llm_fallback_providers: str = "groq,ollama"
    llm_timeout_seconds: float = Field(default=45.0, gt=0, le=300)
    llm_max_retries: int = Field(default=1, ge=0, le=5)
    llm_retry_delay_seconds: float = Field(default=0.5, ge=0, le=30)

    local_ocr_enabled: bool = True
    tesseract_cmd: str = ""
    tesseract_languages: str = "eng"
    tesseract_config: str = "--oem 3 --psm 6"
    ocr_structuring_provider: Literal["gemini", "groq", "ollama"] = "groq"
    ocr_pdf_dpi: int = Field(default=220, ge=72, le=600)
    ocr_max_pdf_pages: int = Field(default=15, ge=1, le=100)

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_chunk_size: int = Field(default=900, ge=200, le=4000)
    rag_chunk_overlap: int = Field(default=140, ge=0, le=1000)

    voice_transcription_enabled: bool = True
    voice_speech_enabled: bool = True
    voice_whisper_model: str = "small"
    voice_whisper_device: str = "cpu"
    voice_whisper_compute_type: str = "int8"
    voice_beam_size: int = Field(default=1, ge=1, le=10)
    voice_max_audio_mb: int = Field(default=15, ge=1, le=100)
    allowed_audio_extensions: str = "wav,mp3,m4a,ogg,webm,flac"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_env(cls, value: object) -> object:
        return str(value or "development").strip().lower()

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, value: str) -> str:
        origins = [item.strip() for item in value.split(",") if item.strip()]
        if not origins:
            raise ValueError("ALLOWED_ORIGINS must contain at least one origin")
        return ",".join(origins)

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.rag_chunk_overlap >= self.rag_chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP must be smaller than RAG_CHUNK_SIZE")

        if self.app_env == "production":
            if self.debug:
                raise ValueError("DEBUG must be false in production")
            if "*" in self.cors_origins:
                raise ValueError("Wildcard CORS origins are not allowed in production")
            if not self.configured_providers:
                raise ValueError(
                    "Production requires at least one configured LLM provider: "
                    "GEMINI_API_KEY, GROQ_API_KEY, or OLLAMA_ENABLED=true"
                )
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def configured_providers(self) -> list[str]:
        providers: list[str] = []
        if self.gemini_api_key.strip():
            providers.append("gemini")
        if self.groq_api_key.strip():
            providers.append("groq")
        if self.ollama_enabled:
            providers.append("ollama")
        return providers

    @property
    def audio_extensions(self) -> set[str]:
        return {item.strip().lower() for item in self.allowed_audio_extensions.split(",") if item.strip()}

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def docs_url(self) -> str | None:
        return "/docs" if self.api_docs_enabled else None

    @property
    def redoc_url(self) -> str | None:
        return "/redoc" if self.api_docs_enabled else None


settings = Settings()
