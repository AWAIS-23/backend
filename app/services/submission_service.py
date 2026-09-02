import uuid
import logging
from datetime import datetime, timezone
from typing import Sequence
from app.core.constants import ChallengeStatus, ErrorCode, SubmissionStatus, UserRole
from app.core.exceptions import (
    AppException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from app.core.security import AuthenticatedUser
from app.core.utils import is_expired
from app.models.submission import Submission
from app.repositories.challenge_repo import ChallengeRepository
from app.repositories.submission_repo import SubmissionRepository
from app.schemas.submission import SubmissionCreate, SubmissionUpdate

logger = logging.getLogger("rising_skills.services.submission")


class SubmissionService:
    def __init__(
        self,
        submission_repo: SubmissionRepository,
        challenge_repo: ChallengeRepository,
    ):
        self.submission_repo = submission_repo
        self.challenge_repo = challenge_repo

    async def create_submission(
        self,
        challenge_id: uuid.UUID,
        profile_id: uuid.UUID,
        data: SubmissionCreate,
    ) -> Submission:
        challenge = await self.challenge_repo.get_by_id(challenge_id)
        if not challenge:
            raise ResourceNotFoundException(resource="Challenge", identifier=challenge_id)

        if challenge.status != ChallengeStatus.PUBLISHED:
            raise PermissionDeniedException("Cannot submit to an unpublished challenge.")

        # Deadline enforcement
        if challenge.submission_deadline and is_expired(challenge.submission_deadline):
            raise AppException(
                status_code=400,
                error_code=ErrorCode.SUBMISSION_DEADLINE_PASSED,
                message="The submission deadline for this practical challenge has passed.",
            )

        now_utc = datetime.now(timezone.utc)
        submission = Submission(
            challenge_id=challenge_id,
            profile_id=profile_id,
            repository_url=data.repository_url,
            deployment_url=data.deployment_url,
            description=data.description,
            status=SubmissionStatus.SUBMITTED,
            submitted_at=now_utc,
        )

        created = await self.submission_repo.create(submission)
        logger.info(f"Learner '{profile_id}' submitted work for challenge '{challenge_id}' (Submission ID: {created.id})")
        return created

    async def get_submission(
        self,
        submission_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> Submission:
        submission = await self.submission_repo.get_with_details(submission_id)
        if not submission:
            raise ResourceNotFoundException(resource="Submission", identifier=submission_id)

        # IDOR Access Control: Owner, Platform Admin, or Employer with evaluator permissions can view
        user_uuid = uuid.UUID(current_user.id)
        is_owner = submission.profile_id == user_uuid
        is_privileged = current_user.role in [UserRole.ADMIN, UserRole.EMPLOYER]

        if not (is_owner or is_privileged):
            raise PermissionDeniedException("You are not authorized to view this submission.")

        return submission

    async def update_submission(
        self,
        submission_id: uuid.UUID,
        profile_id: uuid.UUID,
        data: SubmissionUpdate,
    ) -> Submission:
        submission = await self.submission_repo.get_with_details(submission_id)
        if not submission:
            raise ResourceNotFoundException(resource="Submission", identifier=submission_id)

        # IDOR Ownership check
        if submission.profile_id != profile_id:
            raise PermissionDeniedException("You are not authorized to modify this submission.")

        # State Guard: Once evaluated or accepted, cannot be modified
        if submission.status in [SubmissionStatus.EVALUATED, SubmissionStatus.ACCEPTED]:
            raise AppException(
                status_code=400,
                error_code=ErrorCode.INVALID_SUBMISSION_STATE,
                message=f"Submission cannot be modified in '{submission.status.value}' state.",
            )

        # Deadline check on edit
        if submission.challenge and submission.challenge.submission_deadline and is_expired(submission.challenge.submission_deadline):
            raise AppException(
                status_code=400,
                error_code=ErrorCode.SUBMISSION_DEADLINE_PASSED,
                message="Cannot update submission because the challenge deadline has passed.",
            )

        if data.repository_url is not None:
            submission.repository_url = data.repository_url
        if data.deployment_url is not None:
            submission.deployment_url = data.deployment_url
        if data.description is not None:
            submission.description = data.description

        await self.submission_repo.session.flush()
        await self.submission_repo.session.refresh(submission)
        logger.info(f"Learner '{profile_id}' updated submission '{submission_id}'.")
        return submission

    async def list_challenge_submissions(
        self,
        challenge_id: uuid.UUID,
        current_user: AuthenticatedUser,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Submission]:
        # Privilege check for listing all submissions of a challenge
        if current_user.role not in [UserRole.ADMIN, UserRole.EMPLOYER]:
            raise PermissionDeniedException("Only authorized employers and administrators can list all challenge submissions.")

        return await self.submission_repo.list_for_challenge(challenge_id, skip=skip, limit=limit)
