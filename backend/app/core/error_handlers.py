import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import MediSimplifyException

logger = logging.getLogger("medisimplify")

def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(MediSimplifyException)
    async def medisimplify_exception_handler(request: Request, exc: MediSimplifyException):
        logger.warning(f"Application error on {request.url.path}: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "error_type": exc.__class__.__name__,
                "message": exc.message
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error on {request.url.path}: {str(exc)}")
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error_type": "ValidationError",
                "message": "Invalid input values provided",
                "details": exc.errors()
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        # Log the exception stack trace internally for developers, but redact private details or do not expose them to client
        logger.error(f"Unhandled system error on {request.url.path}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error_type": "InternalServerError",
                "message": "An unexpected error occurred. Please try again later."
            }
        )
