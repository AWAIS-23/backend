import uuid
from datetime import datetime, timezone
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.challenge import Challenge
from app.models.evaluation import Evaluation
from app.models.submission import Submission
from app.repositories.base import BaseRepository


class SubmissionRepository(BaseRepository[Submission]):
    def __init__(self, session: AsyncSession):
        super().__init__(Submission, session)

    async def get_with_details(self, submission_id: uuid.UUID) -> Submission | None:
        stmt = (
            select(Submission)
            .options(
                selectinload(Submission.challenge),
                selectinload(Submission.evaluations),
            )
            .where(Submission.id == submission_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_learner_submission(
        self,
        challenge_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> Submission | None:
        """Returns the most recent submission of this learner for the challenge."""
        stmt = (
            select(Submission)
            .where(
                Submission.challenge_id == challenge_id,
                Submission.profile_id == profile_id,
            )
            .order_by(Submission.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_challenge(
        self,
        challenge_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Submission]:
        stmt = (
            select(Submission)
            .where(Submission.challenge_id == challenge_id)
            .order_by(Submission.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
