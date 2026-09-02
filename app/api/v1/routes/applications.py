import uuid
from fastapi import APIRouter, Depends, Query, status
from app.core.constants import ApplicationStatus, UserRole
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.services import get_application_service
from app.schemas.application import ApplicationPublic, ApplicationStatusUpdate
from app.schemas.common import PaginatedResponse
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get(
    "",
    response_model=PaginatedResponse[ApplicationPublic],
    status_code=status.HTTP_200_OK,
    summary="List candidate applications",
    description="Returns all opportunity applications submitted by the authenticated learner.",
)
async def list_my_applications(
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    application_service: ApplicationService = Depends(get_application_service),
) -> PaginatedResponse[ApplicationPublic]:
    return await application_service.list_learner_applications(
        profile_id=uuid.UUID(current_user.id),
        current_user=current_user,
        status=status_filter,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationPublic,
    status_code=status.HTTP_200_OK,
    summary="Get application details",
    description="Returns detailed application status and cover note. Restricted to the applicant or reviewing employer.",
)
async def get_application(
    application_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationPublic:
    application = await application_service.get_application(
        application_id=application_id,
        current_user=current_user,
    )
    return ApplicationPublic.model_validate(application)


@router.patch(
    "/{application_id}/withdraw",
    response_model=ApplicationPublic,
    status_code=status.HTTP_200_OK,
    summary="Withdraw application",
    description="Allows a candidate to withdraw their active application.",
)
async def withdraw_application(
    application_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationPublic:
    withdrawn = await application_service.withdraw_application(
        application_id=application_id,
        profile_id=uuid.UUID(current_user.id),
    )
    return ApplicationPublic.model_validate(withdrawn)


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationPublic,
    status_code=status.HTTP_200_OK,
    summary="Update application review status",
    description="Allows reviewing employers to transition candidate application status (reviewing, shortlisted, rejected, accepted).",
)
async def update_application_status(
    application_id: uuid.UUID,
    payload: ApplicationStatusUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationPublic:
    updated = await application_service.update_application_status(
        application_id=application_id,
        reviewer_user=current_user,
        new_status=payload.status,
    )
    return ApplicationPublic.model_validate(updated)
