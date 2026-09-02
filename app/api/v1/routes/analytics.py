import uuid
from fastapi import APIRouter, Depends, status
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.services import get_analytics_service
from app.schemas.analytics import OrganizationAnalytics
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Employer Analytics"])


@router.get(
    "/organizations/{organization_id}",
    response_model=OrganizationAnalytics,
    status_code=status.HTTP_200_OK,
    summary="Get organization analytics",
    description="Returns aggregate metrics for an employer organization including opportunities, applications, experiences, match scores, and feedback ratings.",
)
async def get_organization_analytics(
    organization_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> OrganizationAnalytics:
    return await analytics_service.get_organization_analytics(
        organization_id=organization_id,
        current_user=current_user,
    )
