import uuid
from fastapi import APIRouter, Depends, status
from app.core.constants import UserRole
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.services import (
    get_assessment_attempt_service,
    get_assessment_evaluation_service,
)
from app.schemas.assessment_attempt import AnswerSubmitRequest, AnswerSubmitResponse
from app.schemas.assessment_result import AssessmentResultResponse
from app.services.assessment_attempt_service import AssessmentAttemptService
from app.services.assessment_evaluation_service import AssessmentEvaluationService

router = APIRouter(prefix="/attempts", tags=["Assessment Attempts & Evaluation"])


@router.post(
    "/{attempt_id}/answers",
    response_model=AnswerSubmitResponse,
    status_code=status.HTTP_200_OK,
    summary="Record an answer during an active attempt",
    description="Saves or updates a learner's answer for a question within the attempt. Enforces attempt ownership, time limit, and valid choices.",
)
async def submit_answer(
    attempt_id: uuid.UUID,
    payload: AnswerSubmitRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    attempt_service: AssessmentAttemptService = Depends(get_assessment_attempt_service),
) -> AnswerSubmitResponse:
    return await attempt_service.submit_answer(
        attempt_id=attempt_id,
        profile_id=uuid.UUID(current_user.id),
        question_id=payload.question_id,
        selected_option=payload.selected_option,
    )


@router.post(
    "/{attempt_id}/submit",
    response_model=AssessmentResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Finalize and evaluate an assessment attempt",
    description="Finalizes the attempt, runs server-side deterministic scoring, saves an immutable result, and returns performance report.",
)
async def finalize_attempt(
    attempt_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    evaluation_service: AssessmentEvaluationService = Depends(get_assessment_evaluation_service),
) -> AssessmentResultResponse:
    return await evaluation_service.submit_and_evaluate(
        attempt_id=attempt_id,
        profile_id=uuid.UUID(current_user.id),
    )


@router.get(
    "/{attempt_id}/result",
    response_model=AssessmentResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Get assessment result",
    description="Retrieves the evaluation result report for a finalized attempt. Restricted to attempt owner or system administrator.",
)
async def get_attempt_result(
    attempt_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    evaluation_service: AssessmentEvaluationService = Depends(get_assessment_evaluation_service),
) -> AssessmentResultResponse:
    is_admin = current_user.role == UserRole.ADMIN
    return await evaluation_service.get_attempt_result(
        attempt_id=attempt_id,
        profile_id=uuid.UUID(current_user.id),
        is_admin=is_admin,
    )
