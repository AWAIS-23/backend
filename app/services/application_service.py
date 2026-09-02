import math
import uuid
import logging
from datetime import datetime, timezone
from app.core.constants import ApplicationStatus, ErrorCode, OpportunityStatus, OrgRole, UserRole
from app.core.exceptions import (
    AppException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from app.core.security import AuthenticatedUser
from app.core.utils import is_expired
from app.models.application import Application
from app.repositories.application_repo import ApplicationRepository
from app.repositories.opportunity_repo import OpportunityRepository
from app.schemas.application import ApplicationCreate, ApplicationPublic
from app.schemas.common import PaginatedResponse
from app.services.matching_service import MatchingService

logger = logging.getLogger("rising_skills.services.application")


class ApplicationService:
    def __init__(
        self,
        application_repo: ApplicationRepository,
        opportunity_repo: OpportunityRepository,
        matching_service: MatchingService,
    ):
        self.application_repo = application_repo
        self.opportunity_repo = opportunity_repo
        self.matching_service = matching_service

    async def apply_to_opportunity(
        self,
        opportunity_id: uuid.UUID,
        profile_id: uuid.UUID,
        data: ApplicationCreate,
    ) -> Application:
        opportunity = await self.opportunity_repo.get_by_id(opportunity_id)
        if not opportunity:
            raise ResourceNotFoundException(resource="Opportunity", identifier=opportunity_id)

        if opportunity.status != OpportunityStatus.PUBLISHED:
            raise AppException(
                status_code=400,
                error_code=ErrorCode.OPPORTUNITY_NOT_PUBLISHED,
                message="Cannot apply to an opportunity that is not currently published.",
            )

        if opportunity.deadline and is_expired(opportunity.deadline):
            raise AppException(
                status_code=400,
                error_code=ErrorCode.APPLICATION_DEADLINE_PASSED,
                message="The deadline for applications on this opportunity has passed.",
            )

        # Duplicate application prevention
        existing = await self.application_repo.get_by_opportunity_and_profile(opportunity_id, profile_id)
        if existing:
            raise AppException(
                status_code=409,
                error_code=ErrorCode.DUPLICATE_APPLICATION,
                message="You have already submitted an application for this opportunity.",
            )

        application = Application(
            opportunity_id=opportunity_id,
            profile_id=profile_id,
            cover_note=data.cover_note,
            status=ApplicationStatus.SUBMITTED,
            applied_at=datetime.now(timezone.utc),
        )
        created = await self.application_repo.create(application)

        # Trigger deterministic match calculation on application submission
        try:
            await self.matching_service.calculate_and_save_match(opportunity_id, profile_id)
        except Exception as e:
            logger.warning(f"Could not calculate match for application '{created.id}': {str(e)}")

        logger.info(f"Learner '{profile_id}' applied to opportunity '{opportunity_id}' (Application ID: {created.id}).")
        return created

    async def get_application(
        self,
        application_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> Application:
        application = await self.application_repo.get_with_details(application_id)
        if not application:
            raise ResourceNotFoundException(resource="Application", identifier=application_id)

        user_uuid = uuid.UUID(current_user.id)
        is_applicant = application.profile_id == user_uuid
        is_admin = current_user.role == UserRole.ADMIN

        # Check if employer in the opportunity's organization
        is_org_employer = False
        if current_user.role == UserRole.EMPLOYER and application.opportunity:
            org_role = current_user.org_roles.get(str(application.opportunity.organization_id))
            if org_role in [OrgRole.OWNER, OrgRole.ADMIN, OrgRole.RECRUITER, OrgRole.EVALUATOR]:
                is_org_employer = True

        if not (is_applicant or is_admin or is_org_employer):
            raise PermissionDeniedException("You are not authorized to view this application.")

        return application

    async def withdraw_application(
        self,
        application_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> Application:
        application = await self.application_repo.get_by_id(application_id)
        if not application:
            raise ResourceNotFoundException(resource="Application", identifier=application_id)

        # Learner ownership check
        if application.profile_id != profile_id:
            raise PermissionDeniedException("You are not authorized to withdraw another candidate's application.")

        if application.status in [ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED]:
            raise AppException(
                status_code=400,
                error_code=ErrorCode.INVALID_APPLICATION_STATUS,
                message=f"Application cannot be withdrawn in finalized state '{application.status.value}'.",
            )

        application.status = ApplicationStatus.WITHDRAWN
        await self.application_repo.session.flush()
        await self.application_repo.session.refresh(application)
        logger.info(f"Learner '{profile_id}' withdrew application '{application_id}'.")
        return application

    async def update_application_status(
        self,
        application_id: uuid.UUID,
        reviewer_user: AuthenticatedUser,
        new_status: ApplicationStatus,
    ) -> Application:
        application = await self.application_repo.get_with_details(application_id)
        if not application:
            raise ResourceNotFoundException(resource="Application", identifier=application_id)

        # Authorization: Employer in the opportunity's organization or Admin
        if reviewer_user.role != UserRole.ADMIN:
            if not application.opportunity:
                raise PermissionDeniedException("Opportunity for this application could not be verified.")
            org_role = reviewer_user.org_roles.get(str(application.opportunity.organization_id))
            if reviewer_user.role != UserRole.EMPLOYER or org_role not in [OrgRole.OWNER, OrgRole.ADMIN, OrgRole.RECRUITER, OrgRole.EVALUATOR]:
                raise PermissionDeniedException("You lack reviewer permissions for this opportunity's organization.")

        application.status = new_status
        application.reviewed_at = datetime.now(timezone.utc)
        application.reviewed_by = uuid.UUID(reviewer_user.id)
        await self.application_repo.session.flush()
        await self.application_repo.session.refresh(application)
        logger.info(f"Application '{application_id}' status updated to '{new_status.value}' by '{reviewer_user.id}'.")
        return application

    async def list_learner_applications(
        self,
        profile_id: uuid.UUID,
        current_user: AuthenticatedUser,
        status: ApplicationStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[ApplicationPublic]:
        user_uuid = uuid.UUID(current_user.id)
        if current_user.role != UserRole.ADMIN and profile_id != user_uuid:
            raise PermissionDeniedException("You cannot view applications belonging to another user.")

        skip = (page - 1) * page_size
        items, total = await self.application_repo.list_for_profile(
            profile_id=profile_id,
            status=status,
            skip=skip,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse[ApplicationPublic](
            items=[ApplicationPublic.model_validate(a) for a in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def list_opportunity_applications(
        self,
        opportunity_id: uuid.UUID,
        current_user: AuthenticatedUser,
        status: ApplicationStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[ApplicationPublic]:
        opportunity = await self.opportunity_repo.get_by_id(opportunity_id)
        if not opportunity:
            raise ResourceNotFoundException(resource="Opportunity", identifier=opportunity_id)

        # RBAC
        if current_user.role != UserRole.ADMIN:
            org_role = current_user.org_roles.get(str(opportunity.organization_id))
            if current_user.role != UserRole.EMPLOYER or org_role not in [OrgRole.OWNER, OrgRole.ADMIN, OrgRole.RECRUITER, OrgRole.EVALUATOR]:
                raise PermissionDeniedException("You are not authorized to view applications for this opportunity.")

        skip = (page - 1) * page_size
        items, total = await self.application_repo.list_for_opportunity(
            opportunity_id=opportunity_id,
            status=status,
            skip=skip,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse[ApplicationPublic](
            items=[ApplicationPublic.model_validate(a) for a in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
