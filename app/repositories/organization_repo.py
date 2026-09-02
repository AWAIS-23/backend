import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.constants import OrgRole
from app.models.organization import Organization, OrganizationMember
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, session: AsyncSession):
        super().__init__(Organization, session)

    async def list_for_profile(self, profile_id: uuid.UUID) -> Sequence[Organization]:
        stmt = (
            select(Organization)
            .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
            .where(OrganizationMember.profile_id == profile_id)
            .order_by(Organization.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_member(
        self,
        organization_id: uuid.UUID,
        profile_id: uuid.UUID,
        org_role: OrgRole,
    ) -> OrganizationMember:
        member = OrganizationMember(
            organization_id=organization_id,
            profile_id=profile_id,
            org_role=org_role,
        )
        self.session.add(member)
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def get_member(
        self,
        organization_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> OrganizationMember | None:
        stmt = select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.profile_id == profile_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_members(self, organization_id: uuid.UUID) -> Sequence[OrganizationMember]:
        stmt = (
            select(OrganizationMember)
            .options(selectinload(OrganizationMember.profile))
            .where(OrganizationMember.organization_id == organization_id)
            .order_by(OrganizationMember.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
