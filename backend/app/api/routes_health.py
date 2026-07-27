from fastapi import APIRouter
from app.core import constants

router = APIRouter()

@router.get("/health", tags=["Health"])
async def get_health():
    """
    Check the health and status of the MediSimplify API service.
    """
    return {
        "status": "healthy",
        "service": constants.PROJECT_NAME,
        "version": constants.VERSION
    }
