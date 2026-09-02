import uuid
from typing import Sequence
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession):
        super().__init__(Notification, session)

    async def list_for_profile(
        self,
        profile_id: uuid.UUID,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Notification], int]:
        filters = [Notification.profile_id == profile_id]
        if unread_only:
            filters.append(Notification.is_read == False)  # noqa: E712

        count_stmt = select(func.count()).select_from(Notification).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total

    async def mark_as_read(
        self,
        notification_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> Notification | None:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.profile_id == profile_id,
        )
        result = await self.session.execute(stmt)
        notification = result.scalar_one_or_none()
        if notification:
            notification.is_read = True
            await self.session.flush()
        return notification

    async def mark_all_as_read(
        self,
        profile_id: uuid.UUID,
    ) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.profile_id == profile_id,
                Notification.is_read == False,  # noqa: E712
            )
            .values(is_read=True)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
