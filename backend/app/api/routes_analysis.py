from fastapi import APIRouter, status

from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.models.routing_models import (
    ManualRouteRequest,
    RouteAnalysisRequest,
    RoutingResult,
)
from app.services import routing_service, session_service

router = APIRouter(prefix="/analysis", tags=["Analysis Routing"])


@router.post("/route", response_model=RoutingResult, status_code=status.HTTP_200_OK)
async def route_confirmed_report(request: RouteAnalysisRequest) -> RoutingResult:
    session = session_service.get_session(request.report_id)
    if not session:
        raise ResourceNotFoundError(
            "Active report session was not found. Please upload the report again."
        )
    if not session.get("confirmed"):
        raise ValidationError("Confirm the extracted report before analysis routing.")

    result = await routing_service.route_report(
        report_id=request.report_id,
        confirmed_text=str(session.get("raw_text", "")),
        preferred_provider=request.preferred_provider,
    )
    session_service.update_session(request.report_id, {"routing_result": result.model_dump()})
    return result


@router.post(
    "/{report_id}/manual-route",
    response_model=RoutingResult,
    status_code=status.HTTP_200_OK,
)
async def manually_route_report(
    report_id: str,
    request: ManualRouteRequest,
) -> RoutingResult:
    session = session_service.get_session(report_id)
    if not session:
        raise ResourceNotFoundError(
            "Active report session was not found. Please upload the report again."
        )
    if not session.get("confirmed"):
        raise ValidationError("Confirm the extracted report before choosing a route.")

    result = routing_service.apply_manual_route(report_id, request.report_type)
    session_service.update_session(report_id, {"routing_result": result.model_dump()})
    return result
