import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import MediSimplifyException

logger = logging.getLogger("medisimplify")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unavailable")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(MediSimplifyException)
    async def medisimplify_exception_handler(request: Request, exc: MediSimplifyException):
        request_id = _request_id(request)
        logger.warning(
            "Application error on %s [request_id=%s]: %s",
            request.url.path,
            request_id,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            headers={"X-Request-ID": request_id},
            content={
                "status": "error",
                "error_type": exc.__class__.__name__,
                "message": exc.message,
                "request_id": request_id,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = _request_id(request)
        logger.warning(
            "Validation error on %s [request_id=%s]",
            request.url.path,
            request_id,
        )
        # Do not return raw submitted values from Pydantic error contexts.
        details = [
            {
                "location": list(error.get("loc", ())),
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "validation_error"),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            headers={"X-Request-ID": request_id},
            content={
                "status": "error",
                "error_type": "ValidationError",
                "message": "Invalid input values were provided.",
                "details": details,
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        request_id = _request_id(request)
        logger.error(
            "Unhandled system error on %s [request_id=%s]",
            request.url.path,
            request_id,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            headers={"X-Request-ID": request_id},
            content={
                "status": "error",
                "error_type": "InternalServerError",
                "message": (
                    "An unexpected error occurred. Please try again later and "
                    f"share reference ID {request_id} if the problem continues."
                ),
                "request_id": request_id,
            },
        )
