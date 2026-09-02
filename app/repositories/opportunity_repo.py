import uuid
from typing import Sequence
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.constants import OpportunityStatus, OpportunityType
from app.models.opportunity import Opportunity
from app.models.opportunity_skill import OpportunitySkill
from app.repositories.base import BaseRepository


class OpportunityRepository(BaseRepository[Opportunity]):
    def __init__(self, session: AsyncSession):
        super().__init__(Opportunity, session)

    async def list_opportunities(
        self,
        organization_id: uuid.UUID | None = None,
        status: OpportunityStatus | None = OpportunityStatus.PUBLISHED,
        opportunity_type: OpportunityType | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Opportunity], int]:
        filters = []
        if status is not None:
            filters.append(Opportunity.status == status)
        if organization_id is not None:
            filters.append(Opportunity.organization_id == organization_id)
        if opportunity_type is not None:
            filters.append(Opportunity.opportunity_type == opportunity_type)
        if search:
            filters.append(Opportunity.title.ilike(f"%{search.strip()}%"))

        count_stmt = select(func.count()).select_from(Opportunity)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = select(Opportunity).options(selectinload(Opportunity.opportunity_skills))
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.order_by(Opportunity.created_at.desc()).offset(skip).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total

    async def get_with_skills(self, opportunity_id: uuid.UUID) -> Opportunity | None:
        stmt = (
            select(Opportunity)
            .options(
                selectinload(Opportunity.opportunity_skills).selectinload(OpportunitySkill.skill),
                selectinload(Opportunity.organization),
            )
            .where(Opportunity.id == opportunity_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_with_skills(
        self,
        opportunity: Opportunity,
        skill_items: list[tuple[uuid.UUID, float]],
    ) -> Opportunity:
        self.session.add(opportunity)
        await self.session.flush()

        for skill_id, weight in skill_items:
            os = OpportunitySkill(
                opportunity_id=opportunity.id,
                skill_id=skill_id,
                importance_weight=weight,
            )
            self.session.add(os)

        await self.session.flush()
        await self.session.refresh(opportunity)
        return opportunity

    async def set_skills(
        self,
        opportunity_id: uuid.UUID,
        skill_items: list[tuple[uuid.UUID, float]],
    ) -> Sequence[OpportunitySkill]:
        # Delete existing skills for opportunity
        del_stmt = delete(OpportunitySkill).where(OpportunitySkill.opportunity_id == opportunity_id)
        await self.session.execute(del_stmt)

        created_skills = []
        for skill_id, weight in skill_items:
            os = OpportunitySkill(
                opportunity_id=opportunity_id,
                skill_id=skill_id,
                importance_weight=weight,
            )
            self.session.add(os)
            created_skills.append(os)

        await self.session.flush()
        return created_skills
