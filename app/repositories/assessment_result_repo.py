import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.assessment_result import AssessmentResult
from app.repositories.base import BaseRepository


class AssessmentResultRepository(BaseRepository[AssessmentResult]):
    def __init__(self, session: AsyncSession):
        super().__init__(AssessmentResult, session)

    async def get_by_attempt_id(self, attempt_id: uuid.UUID) -> AssessmentResult | None:
        stmt = select(AssessmentResult).where(AssessmentResult.attempt_id == attempt_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
