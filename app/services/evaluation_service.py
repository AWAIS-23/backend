import uuid
import logging
from typing import Sequence
from app.core.constants import (
    ErrorCode,
    EvidenceSourceType,
    EvidenceStatus,
    SubmissionStatus,
    UserRole,
)
from app.core.exceptions import (
    AppException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from app.core.security import AuthenticatedUser
from app.models.evaluation import Evaluation
from app.models.evidence import Evidence
from app.repositories.evaluation_repo import EvaluationRepository
from app.repositories.evidence_repo import EvidenceRepository
from app.repositories.submission_repo import SubmissionRepository
from app.schemas.evaluation import EvaluationCreate

logger = logging.getLogger("rising_skills.services.evaluation")


class EvaluationService:
    def __init__(
        self,
        evaluation_repo: EvaluationRepository,
        submission_repo: SubmissionRepository,
        evidence_repo: EvidenceRepository,
    ):
        self.evaluation_repo = evaluation_repo
        self.submission_repo = submission_repo
        self.evidence_repo = evidence_repo

    async def create_evaluation(
        self,
        submission_id: uuid.UUID,
        evaluator_user: AuthenticatedUser,
        data: EvaluationCreate,
    ) -> Evaluation:
        evaluator_uuid = uuid.UUID(evaluator_user.id)

        # Evaluator Authorization Guard
        if evaluator_user.role not in [UserRole.EMPLOYER, UserRole.ADMIN]:
            raise PermissionDeniedException("Only authorized employers and administrators can submit evaluations.")

        submission = await self.submission_repo.get_with_details(submission_id)
        if not submission:
            raise ResourceNotFoundException(resource="Submission", identifier=submission_id)

        # Self-Evaluation Guard: Learner cannot evaluate their own work
        if submission.profile_id == evaluator_uuid:
            raise AppException(
                status_code=403,
                error_code=ErrorCode.SELF_EVALUATION_FORBIDDEN,
                message="You cannot evaluate your own submission.",
            )

        # Server-Authoritative Deterministic Score Calculation
        total_max = sum(item.max_points for item in data.rubric)
        total_awarded = sum(item.awarded_points for item in data.rubric)

        if total_max <= 0:
            raise AppException(
                status_code=400,
                error_code=ErrorCode.RUBRIC_VALIDATION_ERROR,
                message="Total maximum rubric points must be greater than 0.",
            )

        calculated_score = round((total_awarded / total_max) * 100.0, 2)
        rubric_payload = [item.model_dump() for item in data.rubric]

        evaluation = Evaluation(
            submission_id=submission_id,
            evaluator_id=evaluator_uuid,
            rubric=rubric_payload,
            score=calculated_score,
            feedback=data.feedback,
            status="submitted",
        )
        created_eval = await self.evaluation_repo.create(evaluation)

        # Transition submission status to EVALUATED
        submission.status = SubmissionStatus.EVALUATED
        await self.submission_repo.session.flush()

        # Atomic Evidence Generation for all skills mapped to this challenge
        if submission.challenge and submission.challenge.challenge_skills:
            for cs in submission.challenge.challenge_skills:
                # Check for existing evidence from this evaluation to ensure idempotency
                existing = await self.evidence_repo.find_by_source(
                    source_type=EvidenceSourceType.CHALLENGE_SUBMISSION.value,
                    source_id=created_eval.id,
                    profile_id=submission.profile_id,
                )
                if not existing:
                    evidence = Evidence(
                        profile_id=submission.profile_id,
                        skill_id=cs.skill_id,
                        source_type=EvidenceSourceType.CHALLENGE_SUBMISSION,
                        source_id=created_eval.id,
                        score=calculated_score,
                        evidence_data={
                            "challenge_id": str(submission.challenge_id),
                            "challenge_title": submission.challenge.title,
                            "submission_id": str(submission.id),
                            "evaluator_id": str(evaluator_uuid),
                            "rubric_score": calculated_score,
                        },
                        status=EvidenceStatus.PENDING,
                    )
                    self.evidence_repo.session.add(evidence)

            await self.evidence_repo.session.flush()

        logger.info(
            f"Evaluation created for submission '{submission_id}' by evaluator '{evaluator_uuid}'. "
            f"Score: {calculated_score}%"
        )
        return created_eval

    async def list_evaluations(
        self,
        submission_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> Sequence[Evaluation]:
        submission = await self.submission_repo.get_with_details(submission_id)
        if not submission:
            raise ResourceNotFoundException(resource="Submission", identifier=submission_id)

        user_uuid = uuid.UUID(current_user.id)
        is_owner = submission.profile_id == user_uuid
        is_privileged = current_user.role in [UserRole.ADMIN, UserRole.EMPLOYER]

        if not (is_owner or is_privileged):
            raise PermissionDeniedException("You are not authorized to view evaluations for this submission.")

        return await self.evaluation_repo.list_for_submission(submission_id)
