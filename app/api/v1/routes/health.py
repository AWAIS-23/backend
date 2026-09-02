from fastapi import APIRouter, Depends
from app.core.config import Settings, get_settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def get_api_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Returns the operational status of the API service."""
    return HealthResponse(
        status="ok",
        service="rising-skills-backend",
        environment=settings.APP_ENV,
    )
