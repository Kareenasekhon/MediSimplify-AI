from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_analysis,
    routes_chat,
    routes_extraction,
    routes_health,
    routes_providers,
    routes_report_analysis,
)
from app.core import constants
from app.core.error_handlers import register_error_handlers
from app.core.logging_config import setup_logging

setup_logging()

app = FastAPI(
    title=constants.PROJECT_NAME,
    version=constants.VERSION,
    description=(
        "MediSimplify AI Backend API - Educational Medical Report "
        "Explanation Assistant"
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_health.router, prefix=constants.API_V1_STR)
app.include_router(routes_extraction.router, prefix=constants.API_V1_STR)
app.include_router(routes_providers.router, prefix=constants.API_V1_STR)
app.include_router(routes_analysis.router, prefix=constants.API_V1_STR)
app.include_router(routes_report_analysis.router, prefix=constants.API_V1_STR)
app.include_router(routes_chat.router, prefix=constants.API_V1_STR)

register_error_handlers(app)


@app.get("/", tags=["General"])
async def read_root() -> dict:
    """Return basic API navigation information."""
    return {
        "message": f"Welcome to {constants.PROJECT_NAME}",
        "api_version": constants.VERSION,
        "docs_url": "/docs",
        "health_check_url": f"{constants.API_V1_STR}/health",
    }
