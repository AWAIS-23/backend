import uuid
from datetime import datetime, timezone
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.assessment_answer import AssessmentAnswer
from app.repositories.base import BaseRepository


class AssessmentAnswerRepository(BaseRepository[AssessmentAnswer]):
    def __init__(self, session: AsyncSession):
        super().__init__(AssessmentAnswer, session)

    async def get_answer(
        self,
        attempt_id: uuid.UUID,
        question_id: uuid.UUID,
    ) -> AssessmentAnswer | None:
        stmt = select(AssessmentAnswer).where(
            AssessmentAnswer.attempt_id == attempt_id,
            AssessmentAnswer.question_id == question_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_or_update_answer(
        self,
        attempt_id: uuid.UUID,
        question_id: uuid.UUID,
        selected_option: str,
    ) -> AssessmentAnswer:
        existing = await self.get_answer(attempt_id, question_id)
        if existing:
            existing.selected_option = selected_option
            existing.answered_at = datetime.now(timezone.utc)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        new_answer = AssessmentAnswer(
            attempt_id=attempt_id,
            question_id=question_id,
            selected_option=selected_option,
        )
        self.session.add(new_answer)
        await self.session.flush()
        await self.session.refresh(new_answer)
        return new_answer

    async def list_for_attempt(self, attempt_id: uuid.UUID) -> Sequence[AssessmentAnswer]:
        stmt = (
            select(AssessmentAnswer)
            .where(AssessmentAnswer.attempt_id == attempt_id)
            .order_by(AssessmentAnswer.answered_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
