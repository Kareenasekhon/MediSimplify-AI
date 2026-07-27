from app.core.exceptions import ProviderError
from app.models.llm_models import ProviderName
from app.providers.base_provider import BaseLLMProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.groq_provider import GroqProvider
from app.providers.ollama_provider import OllamaProvider


class ProviderFactory:
    """Create provider adapters without exposing API keys to callers."""

    _provider_classes = {
        ProviderName.GEMINI: GeminiProvider,
        ProviderName.GROQ: GroqProvider,
        ProviderName.OLLAMA: OllamaProvider,
    }

    @classmethod
    def create(cls, provider_name: ProviderName | str) -> BaseLLMProvider:
        try:
            normalized = ProviderName(provider_name)
            provider_class = cls._provider_classes[normalized]
        except (ValueError, KeyError) as exc:
            raise ProviderError(f"Unsupported LLM provider: {provider_name}") from exc
        return provider_class()

    @classmethod
    def all(cls) -> list[BaseLLMProvider]:
        return [provider_class() for provider_class in cls._provider_classes.values()]
