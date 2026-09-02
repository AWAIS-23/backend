import uuid
import logging
from datetime import datetime, timezone
from app.core.constants import AttemptStatus
from app.core.exceptions import PermissionDeniedException, ResourceNotFoundException
from app.models.assessment_result import AssessmentResult
from app.repositories.assessment_attempt_repo import AssessmentAttemptRepository
from app.repositories.assessment_result_repo import AssessmentResultRepository
from app.schemas.assessment_result import AssessmentResultResponse

logger = logging.getLogger("rising_skills.services.evaluation")


class AssessmentEvaluationService:
    def __init__(
        self,
        attempt_repo: AssessmentAttemptRepository,
        result_repo: AssessmentResultRepository,
    ):
        self.attempt_repo = attempt_repo
        self.result_repo = result_repo

    async def submit_and_evaluate(
        self,
        attempt_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> AssessmentResultResponse:
        attempt = await self.attempt_repo.get_by_id_with_details(attempt_id)
        if not attempt:
            raise ResourceNotFoundException(resource="Assessment Attempt", identifier=attempt_id)

        # IDOR Ownership Check
        if attempt.profile_id != profile_id:
            raise PermissionDeniedException("You are not authorized to submit this assessment attempt.")

        # Idempotency & Duplicate Submission Protection: Return existing result if already finalized
        if attempt.status == AttemptStatus.SUBMITTED or attempt.result is not None:
            logger.info(f"Attempt '{attempt_id}' already finalized. Returning existing result.")
            existing_result = attempt.result or await self.result_repo.get_by_attempt_id(attempt_id)
            if existing_result:
                return self._build_result_response(existing_result, attempt.assessment.title, attempt.assessment.passing_score, attempt.assessment_id)

        now_utc = datetime.now(timezone.utc)
        questions = [q for q in attempt.assessment.questions if q.is_active]
        answer_map = {ans.question_id: ans.selected_option for ans in attempt.answers}

        total_questions = len(questions)
        answered_questions = len(answer_map)
        correct_answers = 0
        total_points = 0
        earned_points = 0

        # Deterministic Server-Side Evaluation Algorithm
        for q in questions:
            total_points += q.points
            selected = answer_map.get(q.id)
            if selected is not None and str(selected).strip().lower() == str(q.correct_answer).strip().lower():
                correct_answers += 1
                earned_points += q.points

        score_percentage = (
            round((earned_points / total_points) * 100.0, 2)
            if total_points > 0
            else 0.0
        )
        passed = score_percentage >= attempt.assessment.passing_score

        breakdown = {
            "skill_id": str(attempt.assessment.skill_id),
            "passing_score": attempt.assessment.passing_score,
            "score_percentage": score_percentage,
            "passed": passed,
            "total_points": total_points,
            "earned_points": earned_points,
        }

        result = AssessmentResult(
            attempt_id=attempt.id,
            total_questions=total_questions,
            answered_questions=answered_questions,
            correct_answers=correct_answers,
            total_points=total_points,
            earned_points=earned_points,
            score_percentage=score_percentage,
            passed=passed,
            breakdown=breakdown,
            evaluated_at=now_utc,
        )
        created_result = await self.result_repo.create(result)

        # Transition attempt status to SUBMITTED
        attempt.status = AttemptStatus.SUBMITTED
        attempt.submitted_at = now_utc
        await self.attempt_repo.session.flush()

        logger.info(
            f"Attempt '{attempt_id}' evaluated: Score {earned_points}/{total_points} ({score_percentage}%), Passed: {passed}"
        )

        return self._build_result_response(
            created_result,
            attempt.assessment.title,
            attempt.assessment.passing_score,
            attempt.assessment_id,
        )

    async def get_attempt_result(
        self,
        attempt_id: uuid.UUID,
        profile_id: uuid.UUID,
        is_admin: bool = False,
    ) -> AssessmentResultResponse:
        attempt = await self.attempt_repo.get_by_id_with_details(attempt_id)
        if not attempt:
            raise ResourceNotFoundException(resource="Assessment Attempt", identifier=attempt_id)

        # IDOR Ownership Check
        if not is_admin and attempt.profile_id != profile_id:
            raise PermissionDeniedException("You are not authorized to view results for this attempt.")

        result = attempt.result or await self.result_repo.get_by_attempt_id(attempt_id)
        if not result:
            raise ResourceNotFoundException(resource="Assessment Result", identifier=attempt_id)

        return self._build_result_response(
            result,
            attempt.assessment.title,
            attempt.assessment.passing_score,
            attempt.assessment_id,
        )

    def _build_result_response(
        self,
        result: AssessmentResult,
        assessment_title: str,
        passing_score: int,
        assessment_id: uuid.UUID,
    ) -> AssessmentResultResponse:
        return AssessmentResultResponse(
            id=result.id,
            attempt_id=result.attempt_id,
            assessment_id=assessment_id,
            assessment_title=assessment_title,
            total_questions=result.total_questions,
            answered_questions=result.answered_questions,
            correct_answers=result.correct_answers,
            total_points=result.total_points,
            earned_points=result.earned_points,
            score_percentage=result.score_percentage,
            passed=result.passed,
            passing_score=passing_score,
            evaluated_at=result.evaluated_at,
            breakdown=result.breakdown,
        )
