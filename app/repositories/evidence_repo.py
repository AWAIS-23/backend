import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.evidence import Evidence
from app.repositories.base import BaseRepository


class EvidenceRepository(BaseRepository[Evidence]):
    def __init__(self, session: AsyncSession):
        super().__init__(Evidence, session)

    async def list_for_profile(
        self,
        profile_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Evidence], int]:
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(Evidence).where(
            Evidence.profile_id == profile_id
        )
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Evidence)
            .options(selectinload(Evidence.skill), selectinload(Evidence.verifications))
            .where(Evidence.profile_id == profile_id)
            .order_by(Evidence.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total

    async def get_with_verifications(self, evidence_id: uuid.UUID) -> Evidence | None:
        stmt = (
            select(Evidence)
            .options(
                selectinload(Evidence.skill),
                selectinload(Evidence.verifications),
            )
            .where(Evidence.id == evidence_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_source(
        self,
        source_type: str,
        source_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> Evidence | None:
        stmt = select(Evidence).where(
            Evidence.source_type == source_type,
            Evidence.source_id == source_id,
            Evidence.profile_id == profile_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
