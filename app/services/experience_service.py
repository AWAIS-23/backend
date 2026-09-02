import math
import uuid
import logging
from datetime import datetime, timezone
from app.core.constants import (
    ApplicationStatus,
    ErrorCode,
    ExperienceStatus,
    ExperienceType,
    NotificationType,
    OrgRole,
    UserRole,
    VerificationStatus,
)
from app.core.exceptions import (
    AppException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from app.core.security import AuthenticatedUser
from app.models.experience import Experience
from app.repositories.application_repo import ApplicationRepository
from app.repositories.experience_repo import ExperienceRepository
from app.schemas.common import PaginatedResponse
from app.schemas.experience import ExperienceCreate, ExperiencePublic, ExperienceUpdate
from app.services.notification_service import NotificationService

logger = logging.getLogger("rising_skills.services.experience")


class ExperienceService:
    def __init__(
        self,
        experience_repo: ExperienceRepository,
        application_repo: ApplicationRepository,
        notification_service: NotificationService,
    ):
        self.experience_repo = experience_repo
        self.application_repo = application_repo
        self.notification_service = notification_service

    async def create_experience_from_accepted_application(
        self,
        application_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> Experience:
        application = await self.application_repo.get_with_details(application_id)
        if not application:
            raise ResourceNotFoundException(resource="Application", identifier=application_id)

        if application.status != ApplicationStatus.ACCEPTED:
            raise AppException(
                status_code=400,
                error_code=ErrorCode.APPLICATION_NOT_ACCEPTED,
                message="Cannot instantiate an experience for an application that is not in 'accepted' status.",
            )

        if not application.opportunity:
            raise AppException(status_code=400, message="Application has no associated opportunity.")

        # RBAC Check: Reviewer must be Employer in the opportunity's organization or Admin
        self._verify_org_permission(current_user, application.opportunity.organization_id)

        opportunity = application.opportunity
        exp_type = ExperienceType.INTERNSHIP
        if hasattr(opportunity, "opportunity_type") and opportunity.opportunity_type:
            val = opportunity.opportunity_type.value if hasattr(opportunity.opportunity_type, "value") else str(opportunity.opportunity_type)
            try:
                exp_type = ExperienceType(val)
            except ValueError:
                exp_type = ExperienceType.INTERNSHIP

        experience = Experience(
            profile_id=application.profile_id,
            organization_id=opportunity.organization_id,
            opportunity_id=opportunity.id,
            application_id=application.id,
            title=opportunity.title,
            description=opportunity.description,
            experience_type=exp_type,
            started_at=datetime.now(timezone.utc),
            status=ExperienceStatus.ACTIVE,
            verification_status=VerificationStatus.VERIFIED,
        )
        created = await self.experience_repo.create(experience)

        # Notify learner
        await self.notification_service.create_notification(
            profile_id=application.profile_id,
            title="Experience Activated",
            message=f"Your experience '{opportunity.title}' has been activated by the employer.",
            notification_type=NotificationType.EXPERIENCE_CREATED,
            data={"experience_id": str(created.id), "organization_id": str(opportunity.organization_id)},
        )

        logger.info(f"Experience '{created.id}' created for learner '{application.profile_id}' from accepted application '{application_id}'.")
        return created

    async def create_experience(
        self,
        current_user: AuthenticatedUser,
        data: ExperienceCreate,
    ) -> Experience:
        user_uuid = uuid.UUID(current_user.id)

        if data.organization_id:
            # If creating with organization link, check employer permission or self-assignment restriction
            if current_user.role != UserRole.ADMIN:
                org_role = current_user.org_roles.get(str(data.organization_id))
                if current_user.role != UserRole.EMPLOYER or org_role not in [OrgRole.OWNER, OrgRole.ADMIN, OrgRole.RECRUITER, OrgRole.EVALUATOR]:
                    raise PermissionDeniedException("Learners cannot assign themselves to an employer organization without acceptance.")
            verification_status = VerificationStatus.VERIFIED
        else:
            # Self-reported experience by learner
            verification_status = VerificationStatus.UNVERIFIED

        experience = Experience(
            profile_id=data.profile_id if current_user.role == UserRole.ADMIN or current_user.role == UserRole.EMPLOYER else user_uuid,
            organization_id=data.organization_id,
            opportunity_id=data.opportunity_id,
            application_id=data.application_id,
            title=data.title.strip(),
            description=data.description,
            experience_type=data.experience_type,
            started_at=data.started_at or datetime.now(timezone.utc),
            status=ExperienceStatus.ACTIVE,
            verification_status=verification_status,
        )
        return await self.experience_repo.create(experience)

    async def complete_experience(
        self,
        experience_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> Experience:
        experience = await self.experience_repo.get_with_details(experience_id)
        if not experience:
            raise ResourceNotFoundException(resource="Experience", identifier=experience_id)

        user_uuid = uuid.UUID(current_user.id)
        is_owner = experience.profile_id == user_uuid
        is_employer = False
        if experience.organization_id and current_user.role == UserRole.EMPLOYER:
            org_role = current_user.org_roles.get(str(experience.organization_id))
            if org_role in [OrgRole.OWNER, OrgRole.ADMIN, OrgRole.RECRUITER, OrgRole.EVALUATOR]:
                is_employer = True
        is_admin = current_user.role == UserRole.ADMIN

        if not (is_owner or is_employer or is_admin):
            raise PermissionDeniedException("You are not authorized to complete this experience.")

        if experience.status == ExperienceStatus.COMPLETED:
            raise AppException(
                status_code=400,
                error_code=ErrorCode.EXPERIENCE_ALREADY_COMPLETED,
                message="This experience is already marked as completed.",
            )

        experience.status = ExperienceStatus.COMPLETED
        experience.ended_at = datetime.now(timezone.utc)
        await self.experience_repo.session.flush()
        await self.experience_repo.session.refresh(experience)

        # Notify learner
        await self.notification_service.create_notification(
            profile_id=experience.profile_id,
            title="Experience Completed",
            message=f"Your experience '{experience.title}' has been marked completed.",
            notification_type=NotificationType.EXPERIENCE_COMPLETED,
            data={"experience_id": str(experience.id)},
        )

        logger.info(f"Experience '{experience_id}' completed by user '{current_user.id}'.")
        return experience

    async def get_experience(
        self,
        experience_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> Experience:
        experience = await self.experience_repo.get_with_details(experience_id)
        if not experience:
            raise ResourceNotFoundException(resource="Experience", identifier=experience_id)

        user_uuid = uuid.UUID(current_user.id)
        is_owner = experience.profile_id == user_uuid
        is_employer = False
        if experience.organization_id and current_user.role == UserRole.EMPLOYER:
            org_role = current_user.org_roles.get(str(experience.organization_id))
            if org_role in [OrgRole.OWNER, OrgRole.ADMIN, OrgRole.RECRUITER, OrgRole.EVALUATOR]:
                is_employer = True
        is_admin = current_user.role == UserRole.ADMIN

        if not (is_owner or is_employer or is_admin):
            raise PermissionDeniedException("You are not authorized to view this experience.")

        return experience

    async def list_learner_experiences(
        self,
        profile_id: uuid.UUID,
        current_user: AuthenticatedUser,
        status: ExperienceStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[ExperiencePublic]:
        user_uuid = uuid.UUID(current_user.id)
        if current_user.role != UserRole.ADMIN and profile_id != user_uuid:
            raise PermissionDeniedException("You cannot view experiences belonging to another learner.")

        skip = (page - 1) * page_size
        items, total = await self.experience_repo.list_for_profile(
            profile_id=profile_id,
            status=status,
            skip=skip,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse[ExperiencePublic](
            items=[ExperiencePublic.model_validate(e) for e in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def list_organization_experiences(
        self,
        organization_id: uuid.UUID,
        current_user: AuthenticatedUser,
        status: ExperienceStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[ExperiencePublic]:
        self._verify_org_permission(current_user, organization_id)

        skip = (page - 1) * page_size
        items, total = await self.experience_repo.list_for_organization(
            organization_id=organization_id,
            status=status,
            skip=skip,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse[ExperiencePublic](
            items=[ExperiencePublic.model_validate(e) for e in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

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
