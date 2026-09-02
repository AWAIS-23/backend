import uuid
from typing import Sequence
from fastapi import APIRouter, Depends, Query, status
from app.core.constants import UserRole
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_role
from app.dependencies.services import (
    get_challenge_service,
    get_submission_service,
)
from app.schemas.challenge import (
    ChallengeCreate,
    ChallengeDetailPublic,
    ChallengePublic,
)
from app.schemas.common import PaginatedResponse
from app.schemas.submission import SubmissionCreate, SubmissionPublic
from app.services.challenge_service import ChallengeService
from app.services.submission_service import SubmissionService

router = APIRouter(prefix="/challenges", tags=["Practical Challenges"])


@router.get(
    "",
    response_model=PaginatedResponse[ChallengePublic],
    status_code=status.HTTP_200_OK,
    summary="List practical challenges",
    description="Returns a paginated list of practical challenges available for learners to prove hands-on skills.",
)
async def list_challenges(
    organization_id: uuid.UUID | None = Query(default=None, description="Filter by employer organization ID"),
    search: str | None = Query(default=None, description="Search keyword in challenge title"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    challenge_service: ChallengeService = Depends(get_challenge_service),
) -> PaginatedResponse[ChallengePublic]:
    return await challenge_service.list_challenges(
        organization_id=organization_id,
        search=search,
        page=page,
        page_size=page_size,
        user_role=UserRole.LEARNER,
    )


@router.post(
    "",
    response_model=ChallengePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new practical challenge",
    description="Allows employer organizations and administrators to author practical work challenges.",
)
async def create_challenge(
    payload: ChallengeCreate,
    current_user: AuthenticatedUser = Depends(require_role([UserRole.EMPLOYER, UserRole.ADMIN])),
    challenge_service: ChallengeService = Depends(get_challenge_service),
) -> ChallengePublic:
    created = await challenge_service.create_challenge(
        creator_id=uuid.UUID(current_user.id),
        data=payload,
    )
    return ChallengePublic.model_validate(created)


@router.get(
    "/{challenge_id}",
    response_model=ChallengeDetailPublic,
    status_code=status.HTTP_200_OK,
    summary="Get challenge details",
    description="Returns complete instructions and mapped skills for a practical challenge.",
)
async def get_challenge(
    challenge_id: uuid.UUID,
    challenge_service: ChallengeService = Depends(get_challenge_service),
) -> ChallengeDetailPublic:
    return await challenge_service.get_challenge_detail(
        challenge_id=challenge_id,
        user_role=UserRole.LEARNER,
    )


@router.post(
    "/{challenge_id}/submissions",
    response_model=SubmissionPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Submit practical work for a challenge",
    description="Submits code repository and deployment URLs for evaluation. Deadline and status are enforced.",
)
async def submit_challenge_work(
    challenge_id: uuid.UUID,
    payload: SubmissionCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> SubmissionPublic:
    submission = await submission_service.create_submission(
        challenge_id=challenge_id,
        profile_id=uuid.UUID(current_user.id),
        data=payload,
    )
    return SubmissionPublic.model_validate(submission)


@router.get(
    "/{challenge_id}/submissions",
    response_model=list[SubmissionPublic],
    status_code=status.HTTP_200_OK,
    summary="List all submissions for a challenge",
    description="Allows employers and admins to review all learner submissions for a specific challenge.",
)
async def list_challenge_submissions(
    challenge_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> Sequence[SubmissionPublic]:
    submissions = await submission_service.list_challenge_submissions(
        challenge_id=challenge_id,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )
    return [SubmissionPublic.model_validate(s) for s in submissions]
