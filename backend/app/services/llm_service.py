import asyncio
import json
import logging
import re
from typing import Any

from pydantic import BaseModel, ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.exceptions import ProviderError
from app.models.llm_models import (
    LLMGenerationRequest,
    LLMGenerationResult,
    ProviderName,
    ProviderStatus,
    LLMMessage,
)
from app.providers.provider_factory import ProviderFactory

logger = logging.getLogger("medisimplify")


def _provider_order(requested: ProviderName | None) -> list[ProviderName]:
    first = requested or ProviderName(settings.default_llm_provider)
    configured_fallbacks = [
        ProviderName(value.strip())
        for value in settings.llm_fallback_providers.split(",")
        if value.strip() and value.strip() in ProviderName._value2member_map_
    ]
    return list(dict.fromkeys([first, *configured_fallbacks]))


def parse_json_response(content: str) -> dict[str, Any] | list[Any]:
    """Parse an object/array even when an LLM adds fences or surrounding prose.

    The decoder remains strict about the JSON value itself. It does not attempt to
    repair truncated JSON, silently remove commas, or alter medical content.
    """
    cleaned = content.strip().lstrip("\ufeff")
    fenced = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fenced:
        cleaned = fenced.group(1).strip()

    decoder = json.JSONDecoder()
    last_error: json.JSONDecodeError | None = None

    for index, character in enumerate(cleaned):
        if character not in "{[":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        if isinstance(parsed, (dict, list)):
            return parsed

    logger.debug(
        "Malformed provider JSON response (length=%d, preview=%r)",
        len(content),
        content[:500],
    )
    raise ProviderError("The provider returned malformed JSON.") from last_error


def validate_structured_response(content: str, schema: type[BaseModel]) -> BaseModel:
    try:
        return schema.model_validate(parse_json_response(content))
    except PydanticValidationError as exc:
        raise ProviderError("The provider response did not match the required schema.") from exc


async def generate(request: LLMGenerationRequest) -> LLMGenerationResult:
    failures: list[str] = []
    attempts = 0

    for provider_name in _provider_order(request.provider):
        provider = ProviderFactory.create(provider_name)
        if not provider.is_configured():
            failures.append(f"{provider_name.value}: not configured")
            continue

        for retry_index in range(settings.llm_max_retries + 1):
            attempts += 1
            try:
                content = await provider.generate(
                    request.messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    require_json=request.require_json,
                )
                parsed = parse_json_response(content) if request.require_json else None
                return LLMGenerationResult(
                    provider=provider.name,
                    model=provider.model_name,
                    content=content,
                    parsed_json=parsed,
                    fallback_used=provider.name != (request.provider or ProviderName(settings.default_llm_provider)),
                    attempts=attempts,
                )
            except ProviderError as exc:
                failures.append(f"{provider_name.value}: {exc.message}")
                if retry_index < settings.llm_max_retries:
                    await asyncio.sleep(settings.llm_retry_delay_seconds)

    logger.warning("All configured LLM providers failed: %s", "; ".join(failures))
    raise ProviderError(
        "No LLM provider could complete the request. " + "; ".join(failures)
    )


async def get_provider_statuses(check_connections: bool = False) -> list[ProviderStatus]:
    statuses: list[ProviderStatus] = []
    for provider in ProviderFactory.all():
        configured = provider.is_configured()
        available = configured
        detail = "Configured and ready." if configured else "Configuration is missing."

        if configured and check_connections:
            try:
                await provider.generate(
                    messages=[LLMMessage(role="user", content="Reply OK")],
                    temperature=0.0,
                    max_tokens=1,
                )
            except Exception:
                available = False
                detail = "Configured, but the connection check failed."

        statuses.append(
            ProviderStatus(
                provider=provider.name,
                configured=configured,
                available=available,
                model=provider.model_name,
                detail=detail,
            )
        )
    return statuses
