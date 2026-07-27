from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProviderName(str, Enum):
    GEMINI = "gemini"
    GROQ = "groq"
    OLLAMA = "ollama"


class LLMMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str = Field(min_length=1, max_length=50_000)


class LLMGenerationRequest(BaseModel):
    messages: list[LLMMessage]
    provider: ProviderName | None = None
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    require_json: bool = False


class LLMGenerationResult(BaseModel):
    provider: ProviderName
    model: str
    content: str
    parsed_json: dict[str, Any] | list[Any] | None = None
    fallback_used: bool = False
    attempts: int = 1


class ProviderStatus(BaseModel):
    provider: ProviderName
    configured: bool
    available: bool
    model: str
    detail: str


class ProviderStatusResponse(BaseModel):
    default_provider: ProviderName
    providers: list[ProviderStatus]


class ProviderTestRequest(BaseModel):
    provider: ProviderName | None = None
    prompt: str = Field(
        default="Reply with exactly: MediSimplify provider connection successful.",
        min_length=1,
        max_length=1000,
    )
