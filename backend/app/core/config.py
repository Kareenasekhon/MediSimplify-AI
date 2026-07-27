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
    groq_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
