from app.agents.blood_agent import BloodReportAgent
from app.agents.fallback_agent import FallbackAgent
from app.agents.prescription_agent import PrescriptionAgent
from app.agents.radiology_agent import RadiologyAgent
from app.core.exceptions import ValidationError
from app.models.analysis_models import AnalysisLanguage, ReportAnalysisResponse
from app.models.llm_models import ProviderName
from app.models.routing_models import AgentName, ReportType, RoutingResult


AGENTS = {
    AgentName.BLOOD_AGENT: BloodReportAgent,
    AgentName.PRESCRIPTION_AGENT: PrescriptionAgent,
    AgentName.RADIOLOGY_AGENT: RadiologyAgent,
    AgentName.FALLBACK_AGENT: FallbackAgent,
}


async def explain_report(
    report_id: str,
    confirmed_text: str,
    routing_result: RoutingResult,
    language: AnalysisLanguage,
    preferred_provider: ProviderName | None = None,
) -> ReportAnalysisResponse:
    if not confirmed_text.strip():
        raise ValidationError("The confirmed report text is empty.")
    if routing_result.requires_manual_selection:
        raise ValidationError("Confirm the report type manually before requesting an explanation.")

    agent_class = AGENTS.get(routing_result.selected_agent, FallbackAgent)
    agent = agent_class()
    output, provider_used, model, fallback_used = await agent.explain(
        confirmed_text=confirmed_text,
        language=language,
        provider=preferred_provider,
    )

    return ReportAnalysisResponse(
        report_id=report_id,
        report_type=routing_result.report_type,
        agent_used=routing_result.selected_agent,
        provider_used=provider_used,
        model=model,
        language=language,
        summary=output.summary,
        items=output.items,
        important_notes=output.important_notes,
        unclear_information=output.unclear_information,
        questions_for_doctor=output.questions_for_doctor,
        disclaimer=output.disclaimer,
        fallback_used=fallback_used,
        metadata={"routing_method": routing_result.method},
    )
