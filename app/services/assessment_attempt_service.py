import uuid
import logging
from datetime import datetime, timedelta, timezone
from app.core.constants import AssessmentStatus, AttemptStatus, ErrorCode


from app.core.utils import ensure_utc as _ensure_utc
from app.core.exceptions import (
    AppException,
    AttemptExpiredException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from app.models.assessment_answer import AssessmentAnswer
from app.models.assessment_attempt import AssessmentAttempt
from app.repositories.assessment_answer_repo import AssessmentAnswerRepository
from app.repositories.assessment_attempt_repo import AssessmentAttemptRepository
from app.repositories.assessment_repo import AssessmentRepository
from app.schemas.assessment import AssessmentQuestionPublic, QuestionOption
from app.schemas.assessment_attempt import AnswerSubmitResponse, AttemptStartResponse

logger = logging.getLogger("rising_skills.services.attempt")


class AssessmentAttemptService:
    def __init__(
        self,
        attempt_repo: AssessmentAttemptRepository,
        assessment_repo: AssessmentRepository,
        answer_repo: AssessmentAnswerRepository,
    ):
        self.attempt_repo = attempt_repo
        self.assessment_repo = assessment_repo
        self.answer_repo = answer_repo

    async def start_attempt(
        self,
        assessment_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> AttemptStartResponse:
        assessment = await self.assessment_repo.get_by_id_with_questions(assessment_id)
        if not assessment:
            raise ResourceNotFoundException(resource="Assessment", identifier=assessment_id)

        if assessment.status != AssessmentStatus.PUBLISHED:
            raise PermissionDeniedException("Cannot start attempt on an unpublished assessment.")

        now_utc = datetime.now(timezone.utc)

        # Check for existing in-progress attempt
        active_attempt = await self.attempt_repo.get_active_attempt(assessment_id, profile_id)
        if active_attempt:
            # Check if existing attempt has expired
            if now_utc > _ensure_utc(active_attempt.expires_at):
                active_attempt.status = AttemptStatus.EXPIRED
                await self.attempt_repo.session.flush()
            else:
                # Resume current active attempt
                return self._build_attempt_response(active_attempt, assessment.questions)

        # Calculate server-authoritative timestamps
        started_at = now_utc
        expires_at = started_at + timedelta(seconds=assessment.duration_seconds)
        attempt_count = await self.attempt_repo.count_attempts(assessment_id, profile_id)

        attempt = AssessmentAttempt(
            assessment_id=assessment_id,
            profile_id=profile_id,
            started_at=started_at,
            expires_at=expires_at,
            status=AttemptStatus.IN_PROGRESS,
            attempt_number=attempt_count + 1,
        )
        created_attempt = await self.attempt_repo.create(attempt)
        logger.info(f"User '{profile_id}' started attempt #{created_attempt.attempt_number} for assessment '{assessment_id}'")

        return self._build_attempt_response(created_attempt, assessment.questions)

    async def submit_answer(
        self,
        attempt_id: uuid.UUID,
        profile_id: uuid.UUID,
        question_id: uuid.UUID,
        selected_option: str,
    ) -> AnswerSubmitResponse:
        attempt = await self.attempt_repo.get_by_id_with_details(attempt_id)
        if not attempt:
            raise ResourceNotFoundException(resource="Assessment Attempt", identifier=attempt_id)

        # IDOR Ownership check
        if attempt.profile_id != profile_id:
            raise PermissionDeniedException("You are not authorized to submit answers for this attempt.")

        # Attempt state checks
        if attempt.status != AttemptStatus.IN_PROGRESS:
            raise AppException(
                status_code=400,
                error_code=ErrorCode.ATTEMPT_NOT_IN_PROGRESS,
                message=f"Attempt is currently in '{attempt.status.value}' state and is not accepting answers.",
            )

        now_utc = datetime.now(timezone.utc)
        if now_utc > _ensure_utc(attempt.expires_at):
            attempt.status = AttemptStatus.EXPIRED
            await self.attempt_repo.session.flush()
            raise AttemptExpiredException("Assessment time limit has expired. Answers are no longer accepted.")

        # Find target question in assessment
        target_question = next((q for q in attempt.assessment.questions if q.id == question_id), None)
        if not target_question or not target_question.is_active:
            raise AppException(
                status_code=400,
                error_code=ErrorCode.INVALID_QUESTION_FOR_ASSESSMENT,
                message="The specified question does not belong to this assessment.",
            )

        # Validate selected_option exists in question's option choices
        raw_options = target_question.options if isinstance(target_question.options, list) else []
        valid_option_ids = [str(opt.get("id")) for opt in raw_options if isinstance(opt, dict)]
        if selected_option not in valid_option_ids:
            raise AppException(
                status_code=400,
                error_code=ErrorCode.INVALID_OPTION_SELECTED,
                message=f"Selected option '{selected_option}' is not valid. Valid options: {valid_option_ids}.",
            )

        # Save/upsert the answer
        answer = await self.answer_repo.save_or_update_answer(
            attempt_id=attempt_id,
            question_id=question_id,
            selected_option=selected_option,
        )

        return AnswerSubmitResponse(
            id=answer.id,
            attempt_id=answer.attempt_id,
            question_id=answer.question_id,
            answered_at=answer.answered_at,
        )

    def _build_attempt_response(
        self,
        attempt: AssessmentAttempt,
        questions: list,
    ) -> AttemptStartResponse:
        safe_questions = []
        for q in questions:
            if not getattr(q, "is_active", True):
                continue
            raw_options = q.options if isinstance(q.options, list) else []
            parsed_options = [
                QuestionOption(id=str(opt.get("id")), text=str(opt.get("text")))
                for opt in raw_options
                if isinstance(opt, dict)
            ]
            safe_questions.append(
                AssessmentQuestionPublic(
                    id=q.id,
                    question_text=q.question_text,
                    question_type=q.question_type,
                    options=parsed_options,
                    points=q.points,
                    display_order=q.display_order,
                )
            )

        return AttemptStartResponse(
            id=attempt.id,
            assessment_id=attempt.assessment_id,
            started_at=attempt.started_at,
            expires_at=attempt.expires_at,
            status=attempt.status,
            attempt_number=attempt.attempt_number,
            questions=safe_questions,
        )
