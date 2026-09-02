import uuid
from typing import Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.constants import AssessmentStatus
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.repositories.base import BaseRepository


class AssessmentRepository(BaseRepository[Assessment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Assessment, session)

    async def list_assessments(
        self,
        skill_id: uuid.UUID | None = None,
        role_id: uuid.UUID | None = None,
        status: AssessmentStatus | None = AssessmentStatus.PUBLISHED,
        search: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Assessment], int]:
        filters = []
        if status is not None:
            filters.append(Assessment.status == status)
        if skill_id is not None:
            filters.append(Assessment.skill_id == skill_id)
        if role_id is not None:
            filters.append(Assessment.role_id == role_id)
        if search:
            filters.append(Assessment.title.ilike(f"%{search.strip()}%"))

        count_stmt = select(func.count()).select_from(Assessment)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = select(Assessment).options(selectinload(Assessment.skill))
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.order_by(Assessment.created_at.desc()).offset(skip).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()

        return items, total

    async def get_by_id_with_questions(self, assessment_id: uuid.UUID) -> Assessment | None:
        stmt = (
            select(Assessment)
            .options(
                selectinload(Assessment.skill),
                selectinload(Assessment.questions),
            )
            .where(Assessment.id == assessment_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_with_questions(
        self,
        assessment: Assessment,
        questions: list[AssessmentQuestion],
    ) -> Assessment:
        self.session.add(assessment)
        await self.session.flush()

        for q in questions:
            q.assessment_id = assessment.id
            self.session.add(q)

        await self.session.flush()
        await self.session.refresh(assessment)
        return assessment
