import uuid
import logging
from typing import Sequence
from app.core.constants import OrgRole
from app.core.exceptions import PermissionDeniedException, ResourceNotFoundException
from app.models.organization import Organization, OrganizationMember
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.profile_repo import ProfileRepository
from app.schemas.organization import OrganizationCreate

logger = logging.getLogger("rising_skills.services.organization")


class OrganizationService:
    def __init__(
        self,
        org_repo: OrganizationRepository,
        profile_repo: ProfileRepository,
    ):
        self.org_repo = org_repo
        self.profile_repo = profile_repo

    async def create_organization(
        self,
        creator_id: uuid.UUID,
        data: OrganizationCreate,
    ) -> Organization:
        """
        Creates an organization and automatically assigns creator as Organization Owner.
        """
        # Ensure creator profile exists
        await self.profile_repo.get_or_create(creator_id, default_role="employer")

        org = Organization(
            name=data.name.strip(),
            website_url=data.website_url,
            logo_url=data.logo_url,
        )
        created_org = await self.org_repo.create(org)

        # Add creator as OrgRole.OWNER
        await self.org_repo.add_member(
            organization_id=created_org.id,
            profile_id=creator_id,
            org_role=OrgRole.OWNER,
        )
        logger.info(f"Organization '{created_org.name}' created by user '{creator_id}'.")
        return created_org

    async def get_organization(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        is_platform_admin: bool = False,
    ) -> Organization:
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise ResourceNotFoundException(resource="Organization", identifier=org_id)

        if not is_platform_admin:
            member = await self.org_repo.get_member(organization_id=org_id, profile_id=user_id)
            if not member:
                raise PermissionDeniedException("You are not authorized to view this organization.")

        return org

    async def list_user_organizations(self, user_id: uuid.UUID) -> Sequence[Organization]:
        return await self.org_repo.list_for_profile(user_id)

    async def list_members(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        is_platform_admin: bool = False,
    ) -> Sequence[OrganizationMember]:
        # Check organization existence
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise ResourceNotFoundException(resource="Organization", identifier=org_id)

        if not is_platform_admin:
            member = await self.org_repo.get_member(organization_id=org_id, profile_id=user_id)
            if not member:
                raise PermissionDeniedException("You are not authorized to view this organization's members.")

        return await self.org_repo.list_members(org_id)
