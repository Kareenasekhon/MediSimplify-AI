import asyncio
import logging
from typing import Any

from app.core.config import settings
from app.core.exceptions import ProviderError
from app.models.llm_models import LLMMessage, ProviderName
from app.providers.base_provider import BaseLLMProvider

logger = logging.getLogger("medisimplify")


class GroqProvider(BaseLLMProvider):
    name = ProviderName.GROQ

    def __init__(self) -> None:
        self.model_name = settings.groq_model

    def is_configured(self) -> bool:
        key = settings.groq_api_key.strip()
        return bool(key and not key.startswith("your-"))

    @staticmethod
    def _load_sdk() -> Any:
        try:
            from groq import AsyncGroq
        except ImportError as exc:
            raise ProviderError(
                "Groq SDK is unavailable. Install backend requirements."
            ) from exc
        return AsyncGroq

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float,
        max_tokens: int,
        require_json: bool = False,
    ) -> str:
        if not self.is_configured():
            raise ProviderError("Groq is not configured. Add GROQ_API_KEY to backend/.env.")

        AsyncGroq = self._load_sdk()
        request: dict[str, Any] = {
            "model": self.model_name,
            "messages": [message.model_dump() for message in messages],
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }
        if require_json:
            request["response_format"] = {"type": "json_object"}

        try:
            client = AsyncGroq(api_key=settings.groq_api_key)
            response = await asyncio.wait_for(
                client.chat.completions.create(**request),
                timeout=settings.llm_timeout_seconds,
            )
            content = response.choices[0].message.content
            if not content:
                raise ProviderError("Groq returned an empty response.")
            return content.strip()
        except ProviderError:
            raise
        except asyncio.TimeoutError as exc:
            raise ProviderError("Groq request timed out.") from exc
        except Exception as exc:
            logger.error("Groq generation failed", exc_info=True)
            raise ProviderError(f"Groq generation failed: {exc}") from exc
