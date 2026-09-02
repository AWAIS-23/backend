import uuid
from typing import Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.constants import ExperienceStatus
from app.models.experience import Experience
from app.models.experience_feedback import ExperienceFeedback
from app.repositories.base import BaseRepository


class ExperienceRepository(BaseRepository[Experience]):
    def __init__(self, session: AsyncSession):
        super().__init__(Experience, session)

    async def list_for_profile(
        self,
        profile_id: uuid.UUID,
        status: ExperienceStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Experience], int]:
        filters = [Experience.profile_id == profile_id]
        if status is not None:
            filters.append(Experience.status == status)

        count_stmt = select(func.count()).select_from(Experience).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Experience)
            .options(
                selectinload(Experience.organization),
                selectinload(Experience.opportunity),
                selectinload(Experience.feedbacks),
            )
            .where(*filters)
            .order_by(Experience.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total

    async def list_for_organization(
        self,
        organization_id: uuid.UUID,
        status: ExperienceStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Experience], int]:
        filters = [Experience.organization_id == organization_id]
        if status is not None:
            filters.append(Experience.status == status)

        count_stmt = select(func.count()).select_from(Experience).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Experience)
            .options(
                selectinload(Experience.profile),
                selectinload(Experience.opportunity),
                selectinload(Experience.feedbacks),
            )
            .where(*filters)
            .order_by(Experience.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total

    async def get_with_details(self, experience_id: uuid.UUID) -> Experience | None:
        stmt = (
            select(Experience)
            .options(
                selectinload(Experience.organization),
                selectinload(Experience.opportunity),
                selectinload(Experience.profile),
                selectinload(Experience.feedbacks).selectinload(ExperienceFeedback.reviewer),
            )
            .where(Experience.id == experience_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
