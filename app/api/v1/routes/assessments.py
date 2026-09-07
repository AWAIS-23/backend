import uuid
from fastapi import APIRouter, Depends, Query, status
from app.core.constants import AssessmentStatus, UserRole
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.services import (
    get_assessment_attempt_service,
    get_assessment_service,
)
from app.schemas.assessment import (
    AssessmentPublic,
    AssessmentDetailPublic,
    AssessmentCreate,
    AssessmentQuestionPublic,
    AssessmentQuestionCreate,
)
from app.schemas.assessment_attempt import AttemptStartResponse
from app.schemas.common import PaginatedResponse
from app.services.assessment_attempt_service import AssessmentAttemptService
from app.services.assessment_service import AssessmentService

router = APIRouter(prefix="/assessments", tags=["Assessments"])


@router.post(
    "",
    response_model=AssessmentPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new assessment",
    description="Creates a new assessment with questions. Requires authentication.",
)
async def create_assessment(
    data: AssessmentCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    assessment_service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentPublic:
    assessment = await assessment_service.create_assessment(
        creator_id=uuid.UUID(current_user.id),
        data=data,
    )
    return AssessmentPublic.model_validate(assessment)


@router.get(
    "",
    response_model=PaginatedResponse[AssessmentPublic],
    status_code=status.HTTP_200_OK,
    summary="List available skill assessments",
    description="Returns a paginated list of skill assessments with optional skill, role, status, and keyword search filters. Learners only see published assessments unless an explicit status filter is provided.",
)
async def list_assessments(
    skill_id: uuid.UUID | None = Query(default=None, description="Filter by target skill ID"),
    role_id: uuid.UUID | None = Query(default=None, description="Filter by career role ID"),
    search: str | None = Query(default=None, description="Search keyword in assessment title"),
    assessment_status: AssessmentStatus | None = Query(default=None, alias="status", description="Filter by assessment status (draft, published, archived). If omitted, learners see only published."),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    assessment_service: AssessmentService = Depends(get_assessment_service),
) -> PaginatedResponse[AssessmentPublic]:
    # If an explicit status filter is provided, use it; otherwise default by role
    effective_status = assessment_status if assessment_status is not None else (
        AssessmentStatus.PUBLISHED if current_user.role == UserRole.LEARNER else None
    )
    return await assessment_service.list_assessments(
        skill_id=skill_id,
        role_id=role_id,
        search=search,
        page=page,
        page_size=page_size,
        user_role=current_user.role,
        status_override=effective_status,
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

# Delete assessment endpoint
@router.post(
    "/questions",
    response_model=AssessmentQuestionPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Add a question to Question Bank",
    description="Creates a question in the employer's Question Bank (draft assessment).",
)
async def add_question(
    data: AssessmentQuestionCreate,
    token: AuthenticatedUser = Depends(get_current_user),
    assessment_service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentQuestionPublic:
    # Using a default bank title; could be customized later
    bank_title = f"Question Bank – {token.id}"  # token has id attribute
    return await assessment_service.add_question_to_bank(
        creator_id=uuid.UUID(token.id),
        bank_title=bank_title,
        question_data=data,
    )

@router.delete(
    "/{assessment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an assessment",
    description="Deletes an assessment. Only employer users can delete their own assessments.",
)
async def delete_assessment(
    assessment_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    assessment_service: AssessmentService = Depends(get_assessment_service),
) -> None:
    await assessment_service.delete_assessment(assessment_id, current_user)
