import asyncio
import logging
from typing import Any

from app.core.config import settings
from app.core.exceptions import ProviderError
from app.models.llm_models import LLMMessage, ProviderName
from app.providers.base_provider import BaseLLMProvider

logger = logging.getLogger("medisimplify")


class GeminiProvider(BaseLLMProvider):
    name = ProviderName.GEMINI

    def __init__(self) -> None:
        self.model_name = settings.gemini_model

    def is_configured(self) -> bool:
        key = settings.gemini_api_key.strip()
        return bool(key and not key.startswith("your-"))

    @staticmethod
    def _load_sdk() -> tuple[Any, Any]:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ProviderError(
                "Gemini SDK is unavailable. Install backend requirements."
            ) from exc
        return genai, types

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float,
        max_tokens: int,
        require_json: bool = False,
    ) -> str:
        if not self.is_configured():
            raise ProviderError("Gemini is not configured. Add GEMINI_API_KEY to backend/.env.")

        genai, types = self._load_sdk()
        system_parts = [m.content for m in messages if m.role == "system"]
        conversation = "\n\n".join(
            f"{m.role.upper()}: {m.content}" for m in messages if m.role != "system"
        )
        config_kwargs: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if system_parts:
            config_kwargs["system_instruction"] = "\n\n".join(system_parts)
        if require_json:
            config_kwargs["response_mime_type"] = "application/json"

        def _call() -> str:
            client = genai.Client(api_key=settings.gemini_api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=conversation,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            text = getattr(response, "text", None)
            if not text:
                raise ProviderError("Gemini returned an empty response.")
            return text.strip()

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_call), timeout=settings.llm_timeout_seconds
            )
        except ProviderError:
            raise
        except asyncio.TimeoutError as exc:
            raise ProviderError("Gemini request timed out.") from exc
        except Exception as exc:
            logger.error("Gemini generation failed", exc_info=True)
            raise ProviderError(f"Gemini generation failed: {exc}") from exc
