from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_analysis,
    routes_chat,
    routes_extraction,
    routes_health,
    routes_providers,
    routes_report_analysis,
    routes_voice,
)
from app.core import constants
from app.core.config import settings
from app.core.error_handlers import register_error_handlers
from app.core.logging_config import setup_logging
from app.core.startup import validate_runtime_environment
from app.middleware.rate_limit import InMemoryRateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.security import SecurityHeadersMiddleware

setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_runtime_environment()
    yield


app = FastAPI(
    title=constants.PROJECT_NAME,
    version=constants.VERSION,
    description=(
        "MediSimplify AI Backend API - Educational Medical Report "
        "Explanation Assistant"
    ),
    debug=settings.debug,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    openapi_url="/openapi.json" if settings.api_docs_enabled else None,
    lifespan=lifespan,
)


app.add_middleware(RequestContextMiddleware)
if settings.rate_limit_enabled:
    app.add_middleware(InMemoryRateLimitMiddleware)
if settings.security_headers_enabled:
    app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.include_router(routes_health.router, prefix=constants.API_V1_STR)
app.include_router(routes_extraction.router, prefix=constants.API_V1_STR)
app.include_router(routes_providers.router, prefix=constants.API_V1_STR)
app.include_router(routes_analysis.router, prefix=constants.API_V1_STR)
app.include_router(routes_report_analysis.router, prefix=constants.API_V1_STR)
app.include_router(routes_chat.router, prefix=constants.API_V1_STR)
app.include_router(routes_voice.router, prefix=constants.API_V1_STR)

register_error_handlers(app)


@app.get("/", tags=["General"])
async def read_root() -> dict:
    """Return basic API navigation information."""
    response = {
        "message": f"Welcome to {constants.PROJECT_NAME}",
        "api_version": constants.VERSION,
        "health_check_url": f"{constants.API_V1_STR}/health",
        "environment": settings.app_env,
    }
    if settings.api_docs_enabled:
        response["docs_url"] = "/docs"
    return response
