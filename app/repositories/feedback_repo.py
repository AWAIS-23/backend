import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.experience_feedback import ExperienceFeedback
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository[ExperienceFeedback]):
    def __init__(self, session: AsyncSession):
        super().__init__(ExperienceFeedback, session)

    async def get_by_experience_and_reviewer(
        self,
        experience_id: uuid.UUID,
        reviewer_id: uuid.UUID,
    ) -> ExperienceFeedback | None:
        stmt = select(ExperienceFeedback).where(
            ExperienceFeedback.experience_id == experience_id,
            ExperienceFeedback.reviewer_id == reviewer_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_experience(
        self,
        experience_id: uuid.UUID,
    ) -> Sequence[ExperienceFeedback]:
        stmt = (
            select(ExperienceFeedback)
            .options(
                selectinload(ExperienceFeedback.reviewer),
                selectinload(ExperienceFeedback.organization),
            )
            .where(ExperienceFeedback.experience_id == experience_id)
            .order_by(ExperienceFeedback.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_for_profile(
        self,
        profile_id: uuid.UUID,
    ) -> Sequence[ExperienceFeedback]:
        stmt = (
            select(ExperienceFeedback)
            .options(
                selectinload(ExperienceFeedback.organization),
                selectinload(ExperienceFeedback.experience),
            )
            .where(ExperienceFeedback.profile_id == profile_id)
            .order_by(ExperienceFeedback.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
