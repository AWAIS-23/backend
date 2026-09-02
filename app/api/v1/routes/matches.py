import uuid
from fastapi import APIRouter, Depends, Query, status
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.services import get_matching_service
from app.schemas.common import PaginatedResponse
from app.schemas.match import MatchPublic
from app.services.matching_service import MatchingService

router = APIRouter(prefix="/matches", tags=["Deterministic Matching"])


@router.get(
    "/opportunities",
    response_model=PaginatedResponse[MatchPublic],
    status_code=status.HTTP_200_OK,
    summary="Get matched opportunities for learner",
    description="Returns precomputed deterministic matches and skill breakdowns for the authenticated learner.",
)
async def list_my_opportunity_matches(
    min_score: float = Query(default=0.0, ge=0.0, le=100.0, description="Minimum match percentage"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    matching_service: MatchingService = Depends(get_matching_service),
) -> PaginatedResponse[MatchPublic]:
    return await matching_service.list_matches_for_learner(
        profile_id=uuid.UUID(current_user.id),
        current_user=current_user,
        min_score=min_score,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/opportunities/{opportunity_id}/calculate",
    response_model=MatchPublic,
    status_code=status.HTTP_200_OK,
    summary="Calculate match score on demand",
    description="Executes the deterministic matching engine for the current learner against a specific opportunity.",
)
async def calculate_match(
    opportunity_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    matching_service: MatchingService = Depends(get_matching_service),
) -> MatchPublic:
    match = await matching_service.calculate_and_save_match(
        opportunity_id=opportunity_id,
        profile_id=uuid.UUID(current_user.id),
    )
    return MatchPublic.model_validate(match)
