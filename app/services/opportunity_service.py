import math
import uuid
import logging
from datetime import datetime, timezone
from app.core.constants import OpportunityStatus, OpportunityType, OrgRole, UserRole
from app.core.exceptions import (
    PermissionDeniedException,
    ResourceNotFoundException,
)
from app.core.security import AuthenticatedUser
from app.models.opportunity import Opportunity
from app.repositories.opportunity_repo import OpportunityRepository
from app.schemas.common import PaginatedResponse
from app.schemas.opportunity import (
    OpportunityCreate,
    OpportunityDetailPublic,
    OpportunityPublic,
    OpportunitySkillItem,
    OpportunitySkillPublic,
    OpportunityUpdate,
)

logger = logging.getLogger("rising_skills.services.opportunity")


class OpportunityService:
    def __init__(self, opportunity_repo: OpportunityRepository):
        self.opportunity_repo = opportunity_repo

    async def list_opportunities(
        self,
        organization_id: uuid.UUID | None = None,
        search: str | None = None,
        opportunity_type: OpportunityType | None = None,
        page: int = 1,
        page_size: int = 20,
        user_role: UserRole = UserRole.LEARNER,
    ) -> PaginatedResponse[OpportunityPublic]:
        skip = (page - 1) * page_size
        # Learners only see PUBLISHED opportunities; Admins/Employers can see all when queried
        status_filter = OpportunityStatus.PUBLISHED if user_role == UserRole.LEARNER else None

        items, total = await self.opportunity_repo.list_opportunities(
            organization_id=organization_id,
            status=status_filter,
            opportunity_type=opportunity_type,
            search=search,
            skip=skip,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse[OpportunityPublic](
            items=[OpportunityPublic.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_opportunity_detail(
        self,
        opportunity_id: uuid.UUID,
        user_role: UserRole = UserRole.LEARNER,
    ) -> OpportunityDetailPublic:
        opportunity = await self.opportunity_repo.get_with_skills(opportunity_id)
        if not opportunity:
            raise ResourceNotFoundException(resource="Opportunity", identifier=opportunity_id)

        if user_role == UserRole.LEARNER and opportunity.status != OpportunityStatus.PUBLISHED:
            raise PermissionDeniedException("This opportunity is not currently published or available.")

        skills_public = []
        for os in opportunity.opportunity_skills:
            skills_public.append(
                OpportunitySkillPublic(
                    skill_id=os.skill_id,
                    skill_name=os.skill.name if os.skill else "Unknown Skill",
                    importance_weight=os.importance_weight,
                )
            )

        detail = OpportunityDetailPublic.model_validate(opportunity)
        detail.skills = skills_public
        return detail

    async def create_opportunity(
        self,
        current_user: AuthenticatedUser,
        data: OpportunityCreate,
    ) -> Opportunity:
        self._verify_org_permission(current_user, data.organization_id)

        opportunity = Opportunity(
            organization_id=data.organization_id,
            title=data.title.strip(),
            description=data.description,
            opportunity_type=data.opportunity_type,
            status=OpportunityStatus.DRAFT,
            location=data.location,
            is_remote=data.is_remote,
            deadline=data.deadline,
            created_by=uuid.UUID(current_user.id),
        )

        skill_items = [(s.skill_id, s.importance_weight) for s in data.skills]
        created = await self.opportunity_repo.create_with_skills(opportunity, skill_items)
        logger.info(f"Opportunity '{created.title}' created in draft state for org '{data.organization_id}'.")
        return created

    async def update_opportunity(
        self,
        opportunity_id: uuid.UUID,
        current_user: AuthenticatedUser,
        data: OpportunityUpdate,
    ) -> Opportunity:
        opportunity = await self.opportunity_repo.get_by_id(opportunity_id)
        if not opportunity:
            raise ResourceNotFoundException(resource="Opportunity", identifier=opportunity_id)

        self._verify_org_permission(current_user, opportunity.organization_id)

        if data.title is not None:
            opportunity.title = data.title.strip()
        if data.description is not None:
            opportunity.description = data.description
        if data.opportunity_type is not None:
            opportunity.opportunity_type = data.opportunity_type
        if data.location is not None:
            opportunity.location = data.location
        if data.is_remote is not None:
            opportunity.is_remote = data.is_remote
        if data.deadline is not None:
            opportunity.deadline = data.deadline

        await self.opportunity_repo.session.flush()
        await self.opportunity_repo.session.refresh(opportunity)
        return opportunity

    async def publish_opportunity(
        self,
        opportunity_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> Opportunity:
        opportunity = await self.opportunity_repo.get_by_id(opportunity_id)
        if not opportunity:
            raise ResourceNotFoundException(resource="Opportunity", identifier=opportunity_id)

        self._verify_org_permission(current_user, opportunity.organization_id)

        opportunity.status = OpportunityStatus.PUBLISHED
        opportunity.published_at = datetime.now(timezone.utc)
        await self.opportunity_repo.session.flush()
        await self.opportunity_repo.session.refresh(opportunity)
        logger.info(f"Opportunity '{opportunity.id}' published.")
        return opportunity

    async def close_opportunity(
        self,
        opportunity_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> Opportunity:
        opportunity = await self.opportunity_repo.get_by_id(opportunity_id)
        if not opportunity:
            raise ResourceNotFoundException(resource="Opportunity", identifier=opportunity_id)

        self._verify_org_permission(current_user, opportunity.organization_id)

        opportunity.status = OpportunityStatus.CLOSED
        await self.opportunity_repo.session.flush()
        await self.opportunity_repo.session.refresh(opportunity)
        logger.info(f"Opportunity '{opportunity.id}' closed.")
        return opportunity

    async def set_opportunity_skills(
        self,
        opportunity_id: uuid.UUID,
        current_user: AuthenticatedUser,
        skills: list[OpportunitySkillItem],
    ) -> OpportunityDetailPublic:
        opportunity = await self.opportunity_repo.get_by_id(opportunity_id)
        if not opportunity:
            raise ResourceNotFoundException(resource="Opportunity", identifier=opportunity_id)

        self._verify_org_permission(current_user, opportunity.organization_id)

        skill_items = [(s.skill_id, s.importance_weight) for s in skills]
        await self.opportunity_repo.set_skills(opportunity_id, skill_items)
        return await self.get_opportunity_detail(opportunity_id, user_role=UserRole.EMPLOYER)

    def _verify_org_permission(
        self,
        current_user: AuthenticatedUser,
        organization_id: uuid.UUID,
    ) -> None:
        if current_user.role == UserRole.ADMIN:
            return

        org_role = current_user.org_roles.get(str(organization_id))
        allowed_roles = [OrgRole.OWNER, OrgRole.ADMIN, OrgRole.RECRUITER, OrgRole.EVALUATOR]
        if current_user.role != UserRole.EMPLOYER or org_role not in allowed_roles:
            raise PermissionDeniedException(f"You lack management permissions for organization '{organization_id}'.")
