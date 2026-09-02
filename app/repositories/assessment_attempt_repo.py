import uuid
from datetime import datetime
from typing import Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.constants import AttemptStatus
from app.models.assessment_attempt import AssessmentAttempt
from app.repositories.base import BaseRepository


class AssessmentAttemptRepository(BaseRepository[AssessmentAttempt]):
    def __init__(self, session: AsyncSession):
        super().__init__(AssessmentAttempt, session)

    async def get_by_id_with_details(self, attempt_id: uuid.UUID) -> AssessmentAttempt | None:
        from app.models.assessment import Assessment  # local import to avoid circular

        stmt = (
            select(AssessmentAttempt)
            .options(
                selectinload(AssessmentAttempt.assessment).selectinload(Assessment.questions),
                selectinload(AssessmentAttempt.answers),
                selectinload(AssessmentAttempt.result),
            )
            .where(AssessmentAttempt.id == attempt_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_attempt(
        self,
        assessment_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> AssessmentAttempt | None:
        stmt = select(AssessmentAttempt).where(
            AssessmentAttempt.assessment_id == assessment_id,
            AssessmentAttempt.profile_id == profile_id,
            AssessmentAttempt.status == AttemptStatus.IN_PROGRESS,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_attempts(
        self,
        assessment_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> int:
        stmt = select(func.count()).select_from(AssessmentAttempt).where(
            AssessmentAttempt.assessment_id == assessment_id,
            AssessmentAttempt.profile_id == profile_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
