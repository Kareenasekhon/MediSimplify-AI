import asyncio
import logging

import httpx

from app.core.config import settings
from app.core.exceptions import ProviderError
from app.models.llm_models import LLMMessage, ProviderName
from app.providers.base_provider import BaseLLMProvider

logger = logging.getLogger("medisimplify")


class OllamaProvider(BaseLLMProvider):
    name = ProviderName.OLLAMA

    def __init__(self) -> None:
        self.model_name = settings.ollama_model

    def is_configured(self) -> bool:
        return bool(
            settings.ollama_enabled
            and settings.ollama_base_url.strip()
            and self.model_name.strip()
        )

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float,
        max_tokens: int,
        require_json: bool = False,
    ) -> str:
        if not self.is_configured():
            raise ProviderError(
                "Ollama is disabled or not configured. Set OLLAMA_ENABLED=true "
                "after starting Ollama and installing the configured model."
            )

        payload = {
            "model": self.model_name,
            "messages": [message.model_dump() for message in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if require_json:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                response = await client.post(
                    f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                content = response.json().get("message", {}).get("content")
                if not content:
                    raise ProviderError("Ollama returned an empty response.")
                return content.strip()
        except ProviderError:
            raise
        except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
            raise ProviderError("Ollama request timed out.") from exc
        except httpx.HTTPError as exc:
            logger.error("Ollama generation failed", exc_info=True)
            raise ProviderError(f"Ollama generation failed: {exc}") from exc
