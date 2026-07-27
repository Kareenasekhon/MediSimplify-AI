import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory points to the backend/ folder
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    env: str = "development"
    log_level: str = "INFO"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    default_llm_provider: str = "gemini"
    llm_fallback_providers: str = "groq,ollama"
    llm_timeout_seconds: float = 45.0
    llm_max_retries: int = 1
    llm_retry_delay_seconds: float = 0.5
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_chunk_size: int = 900
    rag_chunk_overlap: int = 140

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
