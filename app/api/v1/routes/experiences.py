import uuid
from typing import Sequence
from fastapi import APIRouter, Depends, Query, status
from app.core.constants import ExperienceStatus, UserRole
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.services import (
    get_experience_service,
    get_feedback_service,
)
from app.schemas.common import PaginatedResponse
from app.schemas.experience import ExperienceCreate, ExperiencePublic
from app.schemas.experience_feedback import (
    ExperienceFeedbackCreate,
    ExperienceFeedbackPublic,
)
from app.services.experience_service import ExperienceService
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/experiences", tags=["Experience & Feedback"])


@router.get(
    "/me",
    response_model=PaginatedResponse[ExperiencePublic],
    status_code=status.HTTP_200_OK,
    summary="List my experiences",
    description="Returns all verified and self-reported practical experiences for the authenticated learner.",
)
async def list_my_experiences(
    status_filter: ExperienceStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    experience_service: ExperienceService = Depends(get_experience_service),
) -> PaginatedResponse[ExperiencePublic]:
    return await experience_service.list_learner_experiences(
        profile_id=uuid.UUID(current_user.id),
        current_user=current_user,
        status=status_filter,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{experience_id}",
    response_model=ExperiencePublic,
    status_code=status.HTTP_200_OK,
    summary="Get experience details",
    description="Returns full metadata for an experience record. Restricted to the learner owner, employer, or admin.",
)
async def get_experience(
    experience_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    experience_service: ExperienceService = Depends(get_experience_service),
) -> ExperiencePublic:
    experience = await experience_service.get_experience(
        experience_id=experience_id,
        current_user=current_user,
    )
    return ExperiencePublic.model_validate(experience)


@router.post(
    "",
    response_model=ExperiencePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create experience",
    description="Records a new practical engagement (self-reported or employer-created).",
)
async def create_experience(
    payload: ExperienceCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    experience_service: ExperienceService = Depends(get_experience_service),
) -> ExperiencePublic:
    created = await experience_service.create_experience(
        current_user=current_user,
        data=payload,
    )
    return ExperiencePublic.model_validate(created)


@router.post(
    "/from-application/{application_id}",
    response_model=ExperiencePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create experience from accepted application",
    description="Instantiates a verified organization experience for a candidate whose application has been accepted.",
)
async def create_experience_from_application(
    application_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    experience_service: ExperienceService = Depends(get_experience_service),
) -> ExperiencePublic:
    created = await experience_service.create_experience_from_accepted_application(
        application_id=application_id,
        current_user=current_user,
    )
    return ExperiencePublic.model_validate(created)


@router.post(
    "/{experience_id}/complete",
    response_model=ExperiencePublic,
    status_code=status.HTTP_200_OK,
    summary="Mark experience completed",
    description="Transitions active experience to completed state and sets completion timestamp.",
)
async def complete_experience(
    experience_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    experience_service: ExperienceService = Depends(get_experience_service),
) -> ExperiencePublic:
    completed = await experience_service.complete_experience(
        experience_id=experience_id,
        current_user=current_user,
    )
    return ExperiencePublic.model_validate(completed)


@router.post(
    "/{experience_id}/feedback",
    response_model=ExperienceFeedbackPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Submit employer performance feedback",
    description="Allows employer reviewers to submit structured ratings and feedback on candidate performance.",
)
async def submit_feedback(
    experience_id: uuid.UUID,
    payload: ExperienceFeedbackCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> ExperienceFeedbackPublic:
    feedback = await feedback_service.submit_feedback(
        experience_id=experience_id,
        reviewer_user=current_user,
        data=payload,
    )
    return ExperienceFeedbackPublic.model_validate(feedback)


@router.get(
    "/{experience_id}/feedback",
    response_model=list[ExperienceFeedbackPublic],
    status_code=status.HTTP_200_OK,
    summary="List feedback for experience",
    description="Retrieves all structured performance reviews submitted for this work experience.",
)
async def list_experience_feedback(
    experience_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> Sequence[ExperienceFeedbackPublic]:
    feedbacks = await feedback_service.list_feedback_for_experience(
        experience_id=experience_id,
        current_user=current_user,
    )
    return [ExperienceFeedbackPublic.model_validate(fb) for fb in feedbacks]
