import uuid
from typing import Sequence
from fastapi import APIRouter, Depends, Query, status
from app.core.constants import ApplicationStatus, OpportunityType, UserRole
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_role
from app.dependencies.services import (
    get_application_service,
    get_matching_service,
    get_opportunity_service,
)
from app.schemas.application import ApplicationCreate, ApplicationPublic
from app.schemas.common import PaginatedResponse
from app.schemas.match import MatchPublic
from app.schemas.opportunity import (
    OpportunityCreate,
    OpportunityDetailPublic,
    OpportunityPublic,
    OpportunitySkillItem,
    OpportunitySkillPublic,
    OpportunityUpdate,
)
from app.services.application_service import ApplicationService
from app.services.matching_service import MatchingService
from app.services.opportunity_service import OpportunityService

router = APIRouter(prefix="/opportunities", tags=["Opportunities & Applications"])


@router.get(
    "",
    response_model=PaginatedResponse[OpportunityPublic],
    status_code=status.HTTP_200_OK,
    summary="List career opportunities",
    description="Returns a paginated list of published opportunities with search and filter options.",
)
async def list_opportunities(
    organization_id: uuid.UUID | None = Query(default=None, description="Filter by employer organization ID"),
    search: str | None = Query(default=None, description="Search keyword in title"),
    opportunity_type: OpportunityType | None = Query(default=None, description="Filter by opportunity type"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    opportunity_service: OpportunityService = Depends(get_opportunity_service),
) -> PaginatedResponse[OpportunityPublic]:
    return await opportunity_service.list_opportunities(
        organization_id=organization_id,
        search=search,
        opportunity_type=opportunity_type,
        page=page,
        page_size=page_size,
        user_role=UserRole.LEARNER,
    )


@router.post(
    "",
    response_model=OpportunityPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new opportunity draft",
    description="Allows employer organizations to create a draft career opportunity with required skills.",
)
async def create_opportunity(
    payload: OpportunityCreate,
    current_user: AuthenticatedUser = Depends(require_role([UserRole.EMPLOYER, UserRole.ADMIN])),
    opportunity_service: OpportunityService = Depends(get_opportunity_service),
) -> OpportunityPublic:
    created = await opportunity_service.create_opportunity(
        current_user=current_user,
        data=payload,
    )
    return OpportunityPublic.model_validate(created)


@router.get(
    "/{opportunity_id}",
    response_model=OpportunityDetailPublic,
    status_code=status.HTTP_200_OK,
    summary="Get opportunity details",
    description="Returns opportunity requirements, mapped skill weights, and employer information.",
)
async def get_opportunity(
    opportunity_id: uuid.UUID,
    opportunity_service: OpportunityService = Depends(get_opportunity_service),
) -> OpportunityDetailPublic:
    return await opportunity_service.get_opportunity_detail(
        opportunity_id=opportunity_id,
        user_role=UserRole.LEARNER,
    )


@router.patch(
    "/{opportunity_id}",
    response_model=OpportunityPublic,
    status_code=status.HTTP_200_OK,
    summary="Update opportunity",
    description="Modifies opportunity details. Restricted to organization managers and administrators.",
)
async def update_opportunity(
    opportunity_id: uuid.UUID,
    payload: OpportunityUpdate,
    current_user: AuthenticatedUser = Depends(require_role([UserRole.EMPLOYER, UserRole.ADMIN])),
    opportunity_service: OpportunityService = Depends(get_opportunity_service),
) -> OpportunityPublic:
    updated = await opportunity_service.update_opportunity(
        opportunity_id=opportunity_id,
        current_user=current_user,
        data=payload,
    )
    return OpportunityPublic.model_validate(updated)


@router.post(
    "/{opportunity_id}/publish",
    response_model=OpportunityPublic,
    status_code=status.HTTP_200_OK,
    summary="Publish opportunity",
    description="Transitions an opportunity from draft to published, making it visible to candidates and matching engines.",
)
async def publish_opportunity(
    opportunity_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_role([UserRole.EMPLOYER, UserRole.ADMIN])),
    opportunity_service: OpportunityService = Depends(get_opportunity_service),
) -> OpportunityPublic:
    published = await opportunity_service.publish_opportunity(
        opportunity_id=opportunity_id,
        current_user=current_user,
    )
    return OpportunityPublic.model_validate(published)


@router.post(
    "/{opportunity_id}/close",
    response_model=OpportunityPublic,
    status_code=status.HTTP_200_OK,
    summary="Close opportunity",
    description="Closes an active opportunity to new applications and matches.",
)
async def close_opportunity(
    opportunity_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_role([UserRole.EMPLOYER, UserRole.ADMIN])),
    opportunity_service: OpportunityService = Depends(get_opportunity_service),
) -> OpportunityPublic:
    closed = await opportunity_service.close_opportunity(
        opportunity_id=opportunity_id,
        current_user=current_user,
    )
    return OpportunityPublic.model_validate(closed)


@router.put(
    "/{opportunity_id}/skills",
    response_model=OpportunityDetailPublic,
    status_code=status.HTTP_200_OK,
    summary="Set required skills for opportunity",
    description="Configures the weighted required skill taxonomy for deterministic matching.",
)
async def set_opportunity_skills(
    opportunity_id: uuid.UUID,
    skills: list[OpportunitySkillItem],
    current_user: AuthenticatedUser = Depends(require_role([UserRole.EMPLOYER, UserRole.ADMIN])),
    opportunity_service: OpportunityService = Depends(get_opportunity_service),
) -> OpportunityDetailPublic:
    return await opportunity_service.set_opportunity_skills(
        opportunity_id=opportunity_id,
        current_user=current_user,
        skills=skills,
    )


@router.get(
    "/{opportunity_id}/skills",
    response_model=list[OpportunitySkillPublic],
    status_code=status.HTTP_200_OK,
    summary="Get required skills for opportunity",
    description="Returns the list of required skills and their relative weights for matching.",
)
async def get_opportunity_skills(
    opportunity_id: uuid.UUID,
    opportunity_service: OpportunityService = Depends(get_opportunity_service),
) -> Sequence[OpportunitySkillPublic]:
    detail = await opportunity_service.get_opportunity_detail(
        opportunity_id=opportunity_id,
        user_role=UserRole.LEARNER,
    )
    return detail.skills


@router.post(
    "/{opportunity_id}/apply",
    response_model=ApplicationPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Apply to an opportunity",
    description="Submits a candidate application and triggers instant deterministic match calculation.",
)
async def apply_to_opportunity(
    opportunity_id: uuid.UUID,
    payload: ApplicationCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationPublic:
    created = await application_service.apply_to_opportunity(
        opportunity_id=opportunity_id,
        profile_id=uuid.UUID(current_user.id),
        data=payload,
    )
    return ApplicationPublic.model_validate(created)


@router.get(
    "/{opportunity_id}/applications",
    response_model=PaginatedResponse[ApplicationPublic],
    status_code=status.HTTP_200_OK,
    summary="List applications for opportunity",
    description="Allows employer recruiters to review candidate applications for this specific opportunity.",
)
async def list_opportunity_applications(
    opportunity_id: uuid.UUID,
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_role([UserRole.EMPLOYER, UserRole.ADMIN])),
    application_service: ApplicationService = Depends(get_application_service),
) -> PaginatedResponse[ApplicationPublic]:
    return await application_service.list_opportunity_applications(
        opportunity_id=opportunity_id,
        current_user=current_user,
        status=status_filter,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{opportunity_id}/matches",
    response_model=PaginatedResponse[MatchPublic],
    status_code=status.HTTP_200_OK,
    summary="Get candidate matches for opportunity",
    description="Returns deterministic skill matching scores and explainable breakdowns for candidate profiles.",
)
async def list_opportunity_matches(
    opportunity_id: uuid.UUID,
    min_score: float = Query(default=0.0, ge=0.0, le=100.0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_role([UserRole.EMPLOYER, UserRole.ADMIN])),
    matching_service: MatchingService = Depends(get_matching_service),
) -> PaginatedResponse[MatchPublic]:
    return await matching_service.list_matches_for_opportunity(
        opportunity_id=opportunity_id,
        current_user=current_user,
        min_score=min_score,
        page=page,
        page_size=page_size,
    )
