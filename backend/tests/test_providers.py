from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.exceptions import ProviderError
from app.main import app
from app.models.llm_models import (
    LLMGenerationRequest,
    LLMMessage,
    ProviderName,
)
from app.providers.provider_factory import ProviderFactory
from app.services import llm_service

client = TestClient(app)


class FakeProvider:
    def __init__(
        self,
        name: ProviderName,
        *,
        configured: bool = True,
        content: str = "ok",
        error: ProviderError | None = None,
    ) -> None:
        self.name = name
        self.model_name = f"fake-{name.value}"
        self._configured = configured
        self._content = content
        self._error = error
        self.generate = AsyncMock(side_effect=self._generate)

    def is_configured(self) -> bool:
        return self._configured

    async def _generate(self, *args, **kwargs) -> str:
        if self._error:
            raise self._error
        return self._content


def test_provider_factory_creates_all_supported_providers() -> None:
    assert ProviderFactory.create("gemini").name == ProviderName.GEMINI
    assert ProviderFactory.create("groq").name == ProviderName.GROQ
    assert ProviderFactory.create("ollama").name == ProviderName.OLLAMA


def test_provider_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ProviderError, match="Unsupported LLM provider"):
        ProviderFactory.create("unknown")


def test_parse_json_response_accepts_json_fence() -> None:
    assert llm_service.parse_json_response('```json\n{"status": "ok"}\n```') == {
        "status": "ok"
    }


def test_parse_json_response_rejects_malformed_json() -> None:
    with pytest.raises(ProviderError, match="malformed JSON"):
        llm_service.parse_json_response("not-json")


@pytest.mark.asyncio
async def test_generate_uses_requested_provider(monkeypatch) -> None:
    fake = FakeProvider(ProviderName.GROQ, content="connected")
    monkeypatch.setattr(ProviderFactory, "create", lambda provider_name: fake)
    monkeypatch.setattr(settings, "llm_max_retries", 0)

    result = await llm_service.generate(
        LLMGenerationRequest(
            provider=ProviderName.GROQ,
            messages=[LLMMessage(role="user", content="hello")],
        )
    )

    assert result.provider == ProviderName.GROQ
    assert result.content == "connected"
    assert result.fallback_used is False


@pytest.mark.asyncio
async def test_generate_falls_back_after_provider_failure(monkeypatch) -> None:
    gemini = FakeProvider(
        ProviderName.GEMINI,
        error=ProviderError("temporary failure"),
    )
    groq = FakeProvider(ProviderName.GROQ, content="fallback worked")

    def fake_create(provider_name):
        return gemini if ProviderName(provider_name) == ProviderName.GEMINI else groq

    monkeypatch.setattr(ProviderFactory, "create", fake_create)
    monkeypatch.setattr(settings, "default_llm_provider", "gemini")
    monkeypatch.setattr(settings, "llm_fallback_providers", "groq")
    monkeypatch.setattr(settings, "llm_max_retries", 0)

    result = await llm_service.generate(
        LLMGenerationRequest(
            messages=[LLMMessage(role="user", content="hello")]
        )
    )

    assert result.provider == ProviderName.GROQ
    assert result.fallback_used is True
    assert result.content == "fallback worked"


@pytest.mark.asyncio
async def test_generate_skips_unconfigured_provider(monkeypatch) -> None:
    unconfigured = FakeProvider(ProviderName.GEMINI, configured=False)
    fallback = FakeProvider(ProviderName.GROQ, content="ok")

    def fake_create(provider_name):
        return unconfigured if ProviderName(provider_name) == ProviderName.GEMINI else fallback

    monkeypatch.setattr(ProviderFactory, "create", fake_create)
    monkeypatch.setattr(settings, "default_llm_provider", "gemini")
    monkeypatch.setattr(settings, "llm_fallback_providers", "groq")
    monkeypatch.setattr(settings, "llm_max_retries", 0)

    result = await llm_service.generate(
        LLMGenerationRequest(messages=[LLMMessage(role="user", content="hello")])
    )
    assert result.provider == ProviderName.GROQ
    unconfigured.generate.assert_not_awaited()


def test_provider_status_endpoint_does_not_expose_keys(monkeypatch) -> None:
    fake = FakeProvider(ProviderName.GEMINI, configured=True)
    monkeypatch.setattr(ProviderFactory, "all", lambda: [fake])

    response = client.get("/api/v1/providers/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["providers"][0]["provider"] == "gemini"
    assert "api_key" not in str(payload).lower()


def test_provider_test_endpoint_uses_service(monkeypatch) -> None:
    async def fake_generate(request):
        from app.models.llm_models import LLMGenerationResult
        return LLMGenerationResult(
            provider=ProviderName.GEMINI,
            model="fake-gemini",
            content="MediSimplify provider connection successful.",
        )

    monkeypatch.setattr(llm_service, "generate", fake_generate)
    response = client.post(
        "/api/v1/providers/test",
        json={"provider": "gemini"},
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "gemini"
