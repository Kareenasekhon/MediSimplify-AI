from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.models.llm_models import ProviderName
from app.models.routing_models import AgentName, ReportType


class AnalysisLanguage(str, Enum):
    ENGLISH = "english"
    HINDI = "hindi"
    PUNJABI = "punjabi"


class AnalysisItem(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    observed_value: str | None = Field(default=None, max_length=200)
    unit: str | None = Field(default=None, max_length=100)
    reference_range: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, max_length=100)
    dosage: str | None = Field(default=None, max_length=300)
    frequency: str | None = Field(default=None, max_length=300)
    duration: str | None = Field(default=None, max_length=300)
    section: str | None = Field(default=None, max_length=200)
    simple_explanation: str = Field(min_length=1, max_length=2000)
    source_text: str | None = Field(default=None, max_length=2000)


class AgentStructuredOutput(BaseModel):
    summary: str = Field(min_length=1, max_length=4000)
    items: list[AnalysisItem] = Field(default_factory=list, max_length=200)
    important_notes: list[str] = Field(default_factory=list, max_length=50)
    unclear_information: list[str] = Field(default_factory=list, max_length=50)
    questions_for_doctor: list[str] = Field(default_factory=list, max_length=20)
    disclaimer: str = Field(min_length=1, max_length=1000)


class ReportAnalysisRequest(BaseModel):
    report_id: str = Field(min_length=1, max_length=200)
    preferred_provider: ProviderName | None = None
    language: AnalysisLanguage = AnalysisLanguage.ENGLISH


class ReportAnalysisResponse(BaseModel):
    report_id: str
    report_type: ReportType
    agent_used: AgentName
    provider_used: ProviderName
    model: str
    language: AnalysisLanguage
    summary: str
    items: list[AnalysisItem] = Field(default_factory=list)
    important_notes: list[str] = Field(default_factory=list)
    unclear_information: list[str] = Field(default_factory=list)
    questions_for_doctor: list[str] = Field(default_factory=list)
    disclaimer: str
    fallback_used: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
