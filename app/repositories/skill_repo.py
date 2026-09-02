import uuid
from typing import Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.skill import Skill
from app.repositories.base import BaseRepository


class SkillRepository(BaseRepository[Skill]):
    def __init__(self, session: AsyncSession):
        super().__init__(Skill, session)

    async def get_by_name(self, name: str) -> Skill | None:
        stmt = select(Skill).where(func.lower(Skill.name) == name.strip().lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_skills(
        self,
        search: str | None = None,
        category: str | None = None,
        parent_skill_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Skill], int]:
        filters = []
        if search:
            filters.append(Skill.name.ilike(f"%{search.strip()}%"))
        if category:
            filters.append(func.lower(Skill.category) == category.strip().lower())
        if parent_skill_id is not None:
            filters.append(Skill.parent_skill_id == parent_skill_id)

        # Count total
        count_stmt = select(func.count()).select_from(Skill)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        # Query items
        stmt = select(Skill)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.order_by(Skill.name.asc()).offset(skip).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()

        return items, total

    async def get_children(self, skill_id: uuid.UUID) -> Sequence[Skill]:
        stmt = select(Skill).where(Skill.parent_skill_id == skill_id).order_by(Skill.name.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
