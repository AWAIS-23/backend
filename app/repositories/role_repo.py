import uuid
from typing import Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.role import Role, RoleSkill
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: AsyncSession):
        super().__init__(Role, session)

    async def list_roles(
        self,
        search: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Role], int]:
        filters = []
        if search:
            filters.append(Role.title.ilike(f"%{search.strip()}%"))

        count_stmt = select(func.count()).select_from(Role)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = select(Role)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.order_by(Role.title.asc()).offset(skip).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()

        return items, total

    async def get_role_with_skills(self, role_id: uuid.UUID) -> Role | None:
        stmt = (
            select(Role)
            .options(
                selectinload(Role.role_skills).joinedload(RoleSkill.skill)
            )
            .where(Role.id == role_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_role_skill(
        self,
        role_id: uuid.UUID,
        skill_id: uuid.UUID,
        importance_weight: float = 1.0,
    ) -> RoleSkill:
        role_skill = RoleSkill(
            role_id=role_id,
            skill_id=skill_id,
            importance_weight=importance_weight,
        )
        self.session.add(role_skill)
        await self.session.flush()
        await self.session.refresh(role_skill)
        return role_skill
