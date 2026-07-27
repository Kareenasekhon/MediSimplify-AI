from fastapi import APIRouter, Query

from app.core.config import settings
from app.models.llm_models import (
    LLMGenerationRequest,
    LLMGenerationResult,
    LLMMessage,
    ProviderName,
    ProviderStatusResponse,
    ProviderTestRequest,
)
from app.services import llm_service

router = APIRouter(prefix="/providers", tags=["LLM Providers"])


@router.get("/status", response_model=ProviderStatusResponse)
async def provider_status(
    check_connections: bool = Query(
        default=False,
        description="When true, performs live provider calls and may consume credits.",
    ),
) -> ProviderStatusResponse:
    """Return provider configuration status without exposing secret keys."""
    return ProviderStatusResponse(
        default_provider=ProviderName(settings.default_llm_provider),
        providers=await llm_service.get_provider_statuses(check_connections),
    )


@router.post("/test", response_model=LLMGenerationResult)
async def test_provider(request: ProviderTestRequest) -> LLMGenerationResult:
    """Development connection test; it does not analyze medical content."""
    generation_request = LLMGenerationRequest(
        provider=request.provider,
        messages=[
            LLMMessage(
                role="system",
                content=(
                    "You are a connection-test assistant. Do not provide medical advice. "
                    "Follow the user's formatting instruction exactly."
                ),
            ),
            LLMMessage(role="user", content=request.prompt),
        ],
        temperature=0.0,
        max_tokens=80,
    )
    return await llm_service.generate(generation_request)
