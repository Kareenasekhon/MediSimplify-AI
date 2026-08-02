import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_configuration_is_development_safe() -> None:
    config = Settings(_env_file=None)
    assert config.app_env == "development"
    assert "http://localhost:8501" in config.cors_origins
    assert config.max_report_size_mb >= 1


def test_origins_are_parsed_and_trimmed() -> None:
    config = Settings(
        _env_file=None,
        app_env="testing",
        allowed_origins="https://one.example, https://two.example",
    )
    assert config.cors_origins == ["https://one.example", "https://two.example"]


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="production",
            allowed_origins="*",
            groq_api_key="configured-for-test",
        )


def test_production_requires_provider() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="production",
            allowed_origins="https://frontend.example",
            gemini_api_key="",
            groq_api_key="",
            ollama_enabled=False,
        )


def test_production_accepts_restricted_origin_and_provider() -> None:
    config = Settings(
        _env_file=None,
        app_env="production",
        allowed_origins="https://frontend.example",
        groq_api_key="configured-for-test",
        api_docs_enabled=False,
    )
    assert config.is_production is True
    assert config.docs_url is None
    assert config.configured_providers == ["groq"]
