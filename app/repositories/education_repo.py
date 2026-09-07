import uuid
from typing import Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.education import Education
from app.repositories.base import BaseRepository


class EducationRepository(BaseRepository[Education]):
    def __init__(self, session: AsyncSession):
        super().__init__(Education, session)

    async def list_for_profile(
        self,
        profile_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Education], int]:
        filters = [Education.profile_id == profile_id]

        count_stmt = select(func.count()).select_from(Education).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Education)
            .where(*filters)
            .order_by(Education.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total

    async def get_by_id_and_profile(
        self,
        education_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> Education | None:
        stmt = (
            select(Education)
            .where(
                Education.id == education_id,
                Education.profile_id == profile_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
