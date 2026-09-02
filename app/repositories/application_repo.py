import uuid
from typing import Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.constants import ApplicationStatus
from app.models.application import Application
from app.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    def __init__(self, session: AsyncSession):
        super().__init__(Application, session)

    async def get_by_opportunity_and_profile(
        self,
        opportunity_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> Application | None:
        stmt = select(Application).where(
            Application.opportunity_id == opportunity_id,
            Application.profile_id == profile_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_details(self, application_id: uuid.UUID) -> Application | None:
        stmt = (
            select(Application)
            .options(
                selectinload(Application.opportunity),
                selectinload(Application.profile),
                selectinload(Application.reviewer),
            )
            .where(Application.id == application_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_opportunity(
        self,
        opportunity_id: uuid.UUID,
        status: ApplicationStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Application], int]:
        filters = [Application.opportunity_id == opportunity_id]
        if status is not None:
            filters.append(Application.status == status)

        count_stmt = select(func.count()).select_from(Application).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Application)
            .options(selectinload(Application.profile))
            .where(*filters)
            .order_by(Application.applied_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total

    async def list_for_profile(
        self,
        profile_id: uuid.UUID,
        status: ApplicationStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Application], int]:
        filters = [Application.profile_id == profile_id]
        if status is not None:
            filters.append(Application.status == status)

        count_stmt = select(func.count()).select_from(Application).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Application)
            .options(selectinload(Application.opportunity))
            .where(*filters)
            .order_by(Application.applied_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total
