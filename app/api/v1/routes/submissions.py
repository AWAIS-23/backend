import uuid
from typing import Sequence
from fastapi import APIRouter, Depends, status
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.services import (
    get_evaluation_service,
    get_submission_service,
)
from app.schemas.evaluation import EvaluationCreate, EvaluationPublic
from app.schemas.submission import SubmissionPublic, SubmissionUpdate
from app.services.evaluation_service import EvaluationService
from app.services.submission_service import SubmissionService

router = APIRouter(prefix="/submissions", tags=["Practical Submissions & Evaluations"])


@router.get(
    "/{submission_id}",
    response_model=SubmissionPublic,
    status_code=status.HTTP_200_OK,
    summary="Get submission details",
    description="Returns submission metadata. Restricted to the submission owner, evaluators, and platform administrators.",
)
async def get_submission(
    submission_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> SubmissionPublic:
    submission = await submission_service.get_submission(
        submission_id=submission_id,
        current_user=current_user,
    )
    return SubmissionPublic.model_validate(submission)


@router.patch(
    "/{submission_id}",
    response_model=SubmissionPublic,
    status_code=status.HTTP_200_OK,
    summary="Update submission",
    description="Allows the submitting learner to update their repository and deployment links before evaluation or deadline.",
)
async def update_submission(
    submission_id: uuid.UUID,
    payload: SubmissionUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> SubmissionPublic:
    updated = await submission_service.update_submission(
        submission_id=submission_id,
        profile_id=uuid.UUID(current_user.id),
        data=payload,
    )
    return SubmissionPublic.model_validate(updated)


@router.post(
    "/{submission_id}/evaluations",
    response_model=EvaluationPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Evaluate a learner submission",
    description="Records a structured rubric evaluation from an authorized evaluator. Score is calculated deterministically on the server and evidence is generated atomically.",
)
async def evaluate_submission(
    submission_id: uuid.UUID,
    payload: EvaluationCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationPublic:
    evaluation = await evaluation_service.create_evaluation(
        submission_id=submission_id,
        evaluator_user=current_user,
        data=payload,
    )
    return EvaluationPublic.model_validate(evaluation)


@router.get(
    "/{submission_id}/evaluations",
    response_model=list[EvaluationPublic],
    status_code=status.HTTP_200_OK,
    summary="List evaluations for a submission",
    description="Retrieves rubric feedback and scores for a submission. Accessible by the submitter and authorized reviewers.",
)
async def list_submission_evaluations(
    submission_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> Sequence[EvaluationPublic]:
    evaluations = await evaluation_service.list_evaluations(
        submission_id=submission_id,
        current_user=current_user,
    )
    return [EvaluationPublic.model_validate(e) for e in evaluations]
