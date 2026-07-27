from enum import Enum

from pydantic import BaseModel, Field

from app.models.llm_models import ProviderName


class ReportType(str, Enum):
    BLOOD_REPORT = "blood_report"
    PRESCRIPTION = "prescription"
    RADIOLOGY_REPORT = "radiology_report"
    MIXED_REPORT = "mixed_report"
    UNKNOWN = "unknown"


class AgentName(str, Enum):
    BLOOD_AGENT = "blood_agent"
    PRESCRIPTION_AGENT = "prescription_agent"
    RADIOLOGY_AGENT = "radiology_agent"
    FALLBACK_AGENT = "fallback_agent"


class RouteAnalysisRequest(BaseModel):
    report_id: str = Field(min_length=1, max_length=200)
    preferred_provider: ProviderName | None = None


class SupervisorLLMDecision(BaseModel):
    report_type: ReportType
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=1000)


class RoutingResult(BaseModel):
    report_id: str
    report_type: ReportType
    confidence: float = Field(ge=0.0, le=1.0)
    selected_agent: AgentName
    reason: str
    warnings: list[str] = Field(default_factory=list)
    requires_manual_selection: bool = False
    method: str = Field(pattern="^(rules|llm|manual|fallback)$")
    provider_used: ProviderName | None = None


class ManualRouteRequest(BaseModel):
    report_type: ReportType
