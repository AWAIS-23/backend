import math
import uuid
import logging
from typing import Any
from app.core.constants import NotificationType
from app.models.notification import Notification
from app.repositories.notification_repo import NotificationRepository
from app.schemas.common import PaginatedResponse
from app.schemas.notification import NotificationPublic

logger = logging.getLogger("rising_skills.services.notification")


class NotificationService:
    def __init__(self, notification_repo: NotificationRepository):
        self.notification_repo = notification_repo

    async def create_notification(
        self,
        profile_id: uuid.UUID,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.APPLICATION_STATUS,
        data: dict[str, Any] | None = None,
    ) -> Notification:
        notification = Notification(
            profile_id=profile_id,
            title=title,
            message=message,
            notification_type=notification_type,
            data=data or {},
            is_read=False,
        )
        created = await self.notification_repo.create(notification)
        logger.info(f"Notification '{created.id}' ({notification_type.value}) dispatched to profile '{profile_id}'.")
        return created

    async def list_notifications(
        self,
        profile_id: uuid.UUID,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[NotificationPublic]:
        skip = (page - 1) * page_size
        items, total = await self.notification_repo.list_for_profile(
            profile_id=profile_id,
            unread_only=unread_only,
            skip=skip,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse[NotificationPublic](
            items=[NotificationPublic.model_validate(n) for n in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def mark_as_read(
        self,
        notification_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> Notification | None:
        return await self.notification_repo.mark_as_read(notification_id, profile_id)

    async def mark_all_as_read(
        self,
        profile_id: uuid.UUID,
    ) -> int:
        return await self.notification_repo.mark_all_as_read(profile_id)
