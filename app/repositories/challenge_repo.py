import uuid
from typing import Sequence
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.constants import ChallengeStatus
from app.models.challenge import Challenge
from app.models.challenge_skill import ChallengeSkill
from app.repositories.base import BaseRepository


class ChallengeRepository(BaseRepository[Challenge]):
    def __init__(self, session: AsyncSession):
        super().__init__(Challenge, session)

    async def list_challenges(
        self,
        status: ChallengeStatus | None = ChallengeStatus.PUBLISHED,
        organization_id: uuid.UUID | None = None,
        created_by: uuid.UUID | None = None,
        search: str | None = None,
        skill_ids: list[uuid.UUID] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Challenge], int]:
        filters = []
        if status is not None:
            filters.append(Challenge.status == status)
        if organization_id is not None:
            # Filter by organization_id directly from challenges table
            filters.append(Challenge.organization_id == organization_id)
        if created_by is not None:
            # Filter by creator
            filters.append(Challenge.created_by == created_by)
        if search:
            filters.append(Challenge.title.ilike(f"%{search.strip()}%"))
        if skill_ids:
            # Join with ChallengeSkill to ensure challenge has at least one of the requested skill IDs
            subq = (
                select(ChallengeSkill.id)
                .where(
                    (ChallengeSkill.challenge_id == Challenge.id) &
                    (ChallengeSkill.skill_id.in_(skill_ids))
                )
            )
            filters.append(exists(subq))

        count_stmt = select(func.count()).select_from(Challenge)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = select(Challenge).options(selectinload(Challenge.challenge_skills))
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.order_by(Challenge.created_at.desc()).offset(skip).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total

    async def get_with_skills(self, challenge_id: uuid.UUID) -> Challenge | None:
        stmt = (
            select(Challenge)
            .options(selectinload(Challenge.challenge_skills).selectinload(ChallengeSkill.skill))
            .where(Challenge.id == challenge_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_with_skills(
        self,
        challenge: Challenge,
        skill_items: list[tuple[uuid.UUID, float]],
    ) -> Challenge:
        self.session.add(challenge)
        await self.session.flush()
        for skill_id, weight in skill_items:
            cs = ChallengeSkill(
                challenge_id=challenge.id,
                skill_id=skill_id,
                importance_weight=weight,
            )
            self.session.add(cs)
        await self.session.flush()
        await self.session.refresh(challenge)
        return challenge
