from pydantic import BaseModel, Field

from app.models.analysis_models import AnalysisLanguage
from app.models.llm_models import ProviderName


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=12_000)


class ChatRequest(BaseModel):
    report_id: str = Field(min_length=1, max_length=200)
    question: str = Field(min_length=2, max_length=4000)
    language: AnalysisLanguage = AnalysisLanguage.ENGLISH
    preferred_provider: ProviderName | None = None
    top_k: int = Field(default=4, ge=1, le=10)


class ChatSource(BaseModel):
    chunk_id: str
    excerpt: str = Field(min_length=1, max_length=1000)
    score: float


class ChatResponse(BaseModel):
    report_id: str
    answer: str
    language: AnalysisLanguage
    provider_used: ProviderName
    model: str
    sources: list[ChatSource] = Field(default_factory=list)
    fallback_used: bool = False
    disclaimer: str


class ClearConversationResponse(BaseModel):
    report_id: str
    cleared: bool
    message: str
