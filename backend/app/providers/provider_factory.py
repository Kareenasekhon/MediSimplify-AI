from functools import lru_cache

from app.core.config import settings
from app.core.exceptions import ProviderError
from app.models.llm_models import ProviderName
from app.providers.base_provider import BaseLLMProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.groq_provider import GroqProvider
from app.providers.ollama_provider import OllamaProvider


class ProviderFactory:
    """Create and optionally reuse provider adapters without exposing API keys."""

    _provider_classes = {
        ProviderName.GEMINI: GeminiProvider,
        ProviderName.GROQ: GroqProvider,
        ProviderName.OLLAMA: OllamaProvider,
    }

    @staticmethod
    @lru_cache(maxsize=3)
    def _cached_create(provider_name: ProviderName) -> BaseLLMProvider:
        return ProviderFactory._provider_classes[provider_name]()

    @classmethod
    def create(cls, provider_name: ProviderName | str) -> BaseLLMProvider:
        try:
            normalized = ProviderName(provider_name)
        except ValueError as exc:
            raise ProviderError(f"Unsupported LLM provider: {provider_name}") from exc

        if normalized not in cls._provider_classes:
            raise ProviderError(f"Unsupported LLM provider: {provider_name}")
        if settings.provider_instance_cache_enabled:
            return cls._cached_create(normalized)
        return cls._provider_classes[normalized]()

    @classmethod
    def all(cls) -> list[BaseLLMProvider]:
        return [cls.create(name) for name in cls._provider_classes]

    @classmethod
    def clear_cache(cls) -> None:
        cls._cached_create.cache_clear()
