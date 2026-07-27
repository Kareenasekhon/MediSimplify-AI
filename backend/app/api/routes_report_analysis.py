from fastapi import APIRouter, status

from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.models.analysis_models import ReportAnalysisRequest, ReportAnalysisResponse
from app.models.routing_models import RoutingResult
from app.services import analysis_service, session_service

router = APIRouter(prefix="/analysis", tags=["Report Explanation"])


@router.post("/explain", response_model=ReportAnalysisResponse, status_code=status.HTTP_200_OK)
async def explain_confirmed_report(request: ReportAnalysisRequest) -> ReportAnalysisResponse:
    session = session_service.get_session(request.report_id)
    if not session:
        raise ResourceNotFoundError(
            "Active report session was not found. Please upload the report again."
        )
    if not session.get("confirmed"):
        raise ValidationError("Confirm the extracted report before requesting an explanation.")

    raw_route = session.get("routing_result")
    if not raw_route:
        raise ValidationError("Route the confirmed report before requesting an explanation.")
    route = RoutingResult.model_validate(raw_route)

    result = await analysis_service.explain_report(
        report_id=request.report_id,
        confirmed_text=str(session.get("raw_text", "")),
        routing_result=route,
        language=request.language,
        preferred_provider=request.preferred_provider,
    )
    session_service.update_session(request.report_id, {"analysis_result": result.model_dump()})
    return result
