import uuid
from fastapi import APIRouter, Depends, Query, status
from app.core.constants import UserRole
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.services import (
    get_assessment_attempt_service,
    get_assessment_service,
)
from app.schemas.assessment import AssessmentDetailPublic, AssessmentPublic
from app.schemas.assessment_attempt import AttemptStartResponse
from app.schemas.common import PaginatedResponse
from app.services.assessment_attempt_service import AssessmentAttemptService
from app.services.assessment_service import AssessmentService

router = APIRouter(prefix="/assessments", tags=["Assessments"])


@router.get(
    "",
    response_model=PaginatedResponse[AssessmentPublic],
    status_code=status.HTTP_200_OK,
    summary="List available skill assessments",
    description="Returns a paginated list of published skill assessments with optional skill, role, and keyword search filters.",
)
async def list_assessments(
    skill_id: uuid.UUID | None = Query(default=None, description="Filter by target skill ID"),
    role_id: uuid.UUID | None = Query(default=None, description="Filter by career role ID"),
    search: str | None = Query(default=None, description="Search keyword in assessment title"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    assessment_service: AssessmentService = Depends(get_assessment_service),
) -> PaginatedResponse[AssessmentPublic]:
    return await assessment_service.list_assessments(
        skill_id=skill_id,
        role_id=role_id,
        search=search,
        page=page,
        page_size=page_size,
        user_role=UserRole.LEARNER,
    )


@router.get(
    "/{assessment_id}",
    response_model=AssessmentDetailPublic,
    status_code=status.HTTP_200_OK,
    summary="Get assessment details and questions",
    description="Returns assessment metadata and questions. CRITICAL: Correct answers are strictly masked.",
)
async def get_assessment(
    assessment_id: uuid.UUID,
    assessment_service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentDetailPublic:
    return await assessment_service.get_assessment_detail(
        assessment_id=assessment_id,
        user_role=UserRole.LEARNER,
    )


@router.post(
    "/{assessment_id}/attempts",
    response_model=AttemptStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start an assessment attempt",
    description="Initializes a timed attempt for the authenticated learner. Returns learner-safe questions with server-authoritative expiration.",
)
async def start_assessment_attempt(
    assessment_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    attempt_service: AssessmentAttemptService = Depends(get_assessment_attempt_service),
) -> AttemptStartResponse:
    return await attempt_service.start_attempt(
        assessment_id=assessment_id,
        profile_id=uuid.UUID(current_user.id),
    )
