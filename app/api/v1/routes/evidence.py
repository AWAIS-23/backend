import uuid
from fastapi import APIRouter, Depends, Query, status
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.services import get_evidence_service
from app.schemas.common import PaginatedResponse
from app.schemas.evidence import EvidencePublic
from app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/evidence", tags=["Skill Evidence"])


@router.get(
    "",
    response_model=PaginatedResponse[EvidencePublic],
    status_code=status.HTTP_200_OK,
    summary="List skill evidence records",
    description="Returns a paginated list of skill evidence records demonstrating practical capability and assessment outcomes.",
)
async def list_evidence(
    profile_id: uuid.UUID | None = Query(default=None, description="Target profile ID (defaults to current user)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    evidence_service: EvidenceService = Depends(get_evidence_service),
) -> PaginatedResponse[EvidencePublic]:
    target_profile = profile_id if profile_id is not None else uuid.UUID(current_user.id)
    return await evidence_service.list_profile_evidence(
        profile_id=target_profile,
        current_user=current_user,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{evidence_id}",
    response_model=EvidencePublic,
    status_code=status.HTTP_200_OK,
    summary="Get evidence detail",
    description="Returns complete provenance, skill linkage, and verification status for a specific evidence item.",
)
async def get_evidence(
    evidence_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    evidence_service: EvidenceService = Depends(get_evidence_service),
) -> EvidencePublic:
    evidence = await evidence_service.get_evidence_detail(
        evidence_id=evidence_id,
        current_user=current_user,
    )
    return EvidencePublic.model_validate(evidence)
