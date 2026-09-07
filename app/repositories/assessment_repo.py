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

    async def delete(self, assessment_id: uuid.UUID) -> None:
        stmt = select(Assessment).where(Assessment.id == assessment_id)
        result = await self.session.execute(stmt)
        assessment = result.scalar_one_or_none()
        if not assessment:
            return  # Service will raise not found
        await self.session.delete(assessment)
        await self.session.commit()

    # New helper methods for Question Bank
    async def get_or_create_question_bank(self, owner_id: uuid.UUID, title: str, skill_id: uuid.UUID) -> Assessment:
        stmt = select(Assessment).where(
            Assessment.created_by == owner_id,
            Assessment.title == title,
            Assessment.status == AssessmentStatus.DRAFT,
        )
        result = await self.session.execute(stmt)
        bank = result.scalar_one_or_none()
        if bank:
            return bank
        # Create new draft assessment to serve as question bank
        bank = Assessment(
            title=title,
            description=None,
            skill_id=skill_id,
            role_id=None,
            difficulty=AssessmentStatus.PUBLISHED,  # placeholder
            duration_seconds=0,
            passing_score=0,
            status=AssessmentStatus.DRAFT,
            created_by=owner_id,
        )
        self.session.add(bank)
        await self.session.flush()
        await self.session.refresh(bank)
        return bank

    async def add_question(self, assessment_id: uuid.UUID, question: AssessmentQuestion) -> AssessmentQuestion:
        question.assessment_id = assessment_id
        self.session.add(question)
        await self.session.flush()
        await self.session.refresh(question)
        return question
