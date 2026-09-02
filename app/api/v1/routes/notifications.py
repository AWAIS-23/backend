import uuid
from fastapi import APIRouter, Depends, Query, status
from app.core.exceptions import ResourceNotFoundException
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.services import get_notification_service
from app.schemas.common import PaginatedResponse
from app.schemas.notification import NotificationPublic
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["In-App Notifications"])


@router.get(
    "",
    response_model=PaginatedResponse[NotificationPublic],
    status_code=status.HTTP_200_OK,
    summary="List notifications",
    description="Returns a paginated list of notifications for the authenticated user.",
)
async def list_notifications(
    unread_only: bool = Query(default=False, description="Filter for unread notifications only"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> PaginatedResponse[NotificationPublic]:
    return await notification_service.list_notifications(
        profile_id=uuid.UUID(current_user.id),
        unread_only=unread_only,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationPublic,
    status_code=status.HTTP_200_OK,
    summary="Mark notification as read",
    description="Updates notification read state to true.",
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationPublic:
    updated = await notification_service.mark_as_read(
        notification_id=notification_id,
        profile_id=uuid.UUID(current_user.id),
    )
    if not updated:
        raise ResourceNotFoundException(resource="Notification", identifier=notification_id)
    return NotificationPublic.model_validate(updated)


@router.post(
    "/read-all",
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read",
    description="Marks all unread notifications for current user as read.",
)
async def mark_all_notifications_read(
    current_user: AuthenticatedUser = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> dict[str, int]:
    count = await notification_service.mark_all_as_read(uuid.UUID(current_user.id))
    return {"marked_read": count}
