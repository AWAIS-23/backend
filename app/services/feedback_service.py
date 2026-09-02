import uuid
import logging
from typing import Sequence
from app.core.constants import ErrorCode, NotificationType, OrgRole, UserRole
from app.core.exceptions import (
    AppException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from app.core.security import AuthenticatedUser
from app.models.experience_feedback import ExperienceFeedback
from app.repositories.experience_repo import ExperienceRepository
from app.repositories.feedback_repo import FeedbackRepository
from app.schemas.experience_feedback import ExperienceFeedbackCreate
from app.services.notification_service import NotificationService

logger = logging.getLogger("rising_skills.services.feedback")


class FeedbackService:
    def __init__(
        self,
        feedback_repo: FeedbackRepository,
        experience_repo: ExperienceRepository,
        notification_service: NotificationService,
    ):
        self.feedback_repo = feedback_repo
        self.experience_repo = experience_repo
        self.notification_service = notification_service

    async def submit_feedback(
        self,
        experience_id: uuid.UUID,
        reviewer_user: AuthenticatedUser,
        data: ExperienceFeedbackCreate,
    ) -> ExperienceFeedback:
        experience = await self.experience_repo.get_with_details(experience_id)
        if not experience:
            raise ResourceNotFoundException(resource="Experience", identifier=experience_id)

        reviewer_uuid = uuid.UUID(reviewer_user.id)

        # RBAC: Only authorized employer in the experience's organization or Admin can submit feedback
        if reviewer_user.role != UserRole.ADMIN:
            if not experience.organization_id:
                raise PermissionDeniedException("Cannot submit employer feedback for non-organizational experience.")
            org_role = reviewer_user.org_roles.get(str(experience.organization_id))
            if reviewer_user.role != UserRole.EMPLOYER or org_role not in [OrgRole.OWNER, OrgRole.ADMIN, OrgRole.RECRUITER, OrgRole.EVALUATOR]:
                raise PermissionDeniedException("You lack reviewer permissions for this experience's organization.")

        # Prevent duplicate feedback from same reviewer
        existing = await self.feedback_repo.get_by_experience_and_reviewer(experience_id, reviewer_uuid)
        if existing:
            raise AppException(
                status_code=409,
                error_code=ErrorCode.DUPLICATE_FEEDBACK,
                message="You have already submitted feedback for this experience.",
            )

        feedback = ExperienceFeedback(
            experience_id=experience_id,
            profile_id=experience.profile_id,
            organization_id=experience.organization_id,
            reviewer_id=reviewer_uuid,
            overall_rating=data.overall_rating,
            strengths=data.strengths,
            areas_for_improvement=data.areas_for_improvement,
            communication_rating=data.communication_rating,
            technical_rating=data.technical_rating,
            problem_solving_rating=data.problem_solving_rating,
            teamwork_rating=data.teamwork_rating,
            professionalism_rating=data.professionalism_rating,
            recommendation=data.recommendation,
        )
        created = await self.feedback_repo.create(feedback)

        # Notify learner of new feedback
        await self.notification_service.create_notification(
            profile_id=experience.profile_id,
            title="Feedback Received",
            message=f"You received a {data.overall_rating}/5 performance feedback rating from your employer.",
            notification_type=NotificationType.FEEDBACK_SUBMITTED,
            data={"experience_id": str(experience_id), "feedback_id": str(created.id)},
        )

        logger.info(f"Feedback '{created.id}' submitted for experience '{experience_id}' by reviewer '{reviewer_uuid}'. Rating: {data.overall_rating}/5.")
        return created

    async def list_feedback_for_experience(
        self,
        experience_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> Sequence[ExperienceFeedback]:
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
            raise PermissionDeniedException("You are not authorized to view feedback for this experience.")

        return await self.feedback_repo.list_for_experience(experience_id)

    async def list_feedback_for_learner(
        self,
        profile_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> Sequence[ExperienceFeedback]:
        user_uuid = uuid.UUID(current_user.id)
        if current_user.role != UserRole.ADMIN and profile_id != user_uuid:
            raise PermissionDeniedException("You are not authorized to view feedback for another learner.")

        return await self.feedback_repo.list_for_profile(profile_id)
