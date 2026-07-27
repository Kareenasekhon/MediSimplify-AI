from abc import ABC, abstractmethod

from app.models.llm_models import LLMMessage, ProviderName


class BaseLLMProvider(ABC):
    """Common contract implemented by every text-generation provider."""

    name: ProviderName
    model_name: str

    @abstractmethod
    def is_configured(self) -> bool:
        """Return whether the provider has the configuration needed to run."""

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float,
        max_tokens: int,
        require_json: bool = False,
    ) -> str:
        """Generate one text response or raise ProviderError."""
