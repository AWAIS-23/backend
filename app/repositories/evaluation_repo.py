import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.evaluation import Evaluation
from app.repositories.base import BaseRepository


class EvaluationRepository(BaseRepository[Evaluation]):
    def __init__(self, session: AsyncSession):
        super().__init__(Evaluation, session)

    async def list_for_submission(
        self,
        submission_id: uuid.UUID,
    ) -> Sequence[Evaluation]:
        stmt = (
            select(Evaluation)
            .where(Evaluation.submission_id == submission_id)
            .order_by(Evaluation.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_evaluator_evaluation(
        self,
        submission_id: uuid.UUID,
        evaluator_id: uuid.UUID,
    ) -> Evaluation | None:
        """Returns the existing evaluation from this evaluator for this submission (if any)."""
        stmt = select(Evaluation).where(
            Evaluation.submission_id == submission_id,
            Evaluation.evaluator_id == evaluator_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
