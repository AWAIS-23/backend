import uuid
from typing import Any, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.match import Match
from app.repositories.base import BaseRepository


class MatchingRepository(BaseRepository[Match]):
    def __init__(self, session: AsyncSession):
        super().__init__(Match, session)

    async def get_match(
        self,
        opportunity_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> Match | None:
        stmt = select(Match).where(
            Match.opportunity_id == opportunity_id,
            Match.profile_id == profile_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_or_update_match(
        self,
        opportunity_id: uuid.UUID,
        profile_id: uuid.UUID,
        overall_score: float,
        skill_score: float,
        evidence_score: float,
        experience_score: float,
        breakdown: dict[str, Any],
    ) -> Match:
        existing = await self.get_match(opportunity_id, profile_id)
        if existing:
            existing.overall_score = overall_score
            existing.skill_score = skill_score
            existing.evidence_score = evidence_score
            existing.experience_score = experience_score
            existing.breakdown = breakdown
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        match = Match(
            opportunity_id=opportunity_id,
            profile_id=profile_id,
            overall_score=overall_score,
            skill_score=skill_score,
            evidence_score=evidence_score,
            experience_score=experience_score,
            breakdown=breakdown,
        )
        self.session.add(match)
        await self.session.flush()
        await self.session.refresh(match)
        return match

    async def list_matches_for_opportunity(
        self,
        opportunity_id: uuid.UUID,
        min_score: float = 0.0,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Match], int]:
        filters = [
            Match.opportunity_id == opportunity_id,
            Match.overall_score >= min_score,
        ]
        count_stmt = select(func.count()).select_from(Match).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Match)
            .options(selectinload(Match.profile))
            .where(*filters)
            .order_by(Match.overall_score.desc())
            .offset(skip)
            .limit(limit)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total

    async def list_matches_for_profile(
        self,
        profile_id: uuid.UUID,
        min_score: float = 0.0,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Match], int]:
        filters = [
            Match.profile_id == profile_id,
            Match.overall_score >= min_score,
        ]
        count_stmt = select(func.count()).select_from(Match).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Match)
            .options(selectinload(Match.opportunity))
            .where(*filters)
            .order_by(Match.overall_score.desc())
            .offset(skip)
            .limit(limit)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total
