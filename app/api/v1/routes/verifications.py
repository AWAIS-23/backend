import uuid
from typing import Sequence
from fastapi import APIRouter, Depends, status
from app.core.constants import UserRole
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_role
from app.dependencies.services import get_verification_service
from app.schemas.verification import VerificationCreate, VerificationPublic
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/verifications", tags=["Evidence Verification"])


@router.post(
    "",
    response_model=VerificationPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Verify or reject skill evidence",
    description="Authorized human verifiers approve or reject candidate evidence through controlled state transitions. Self-verification is strictly blocked.",
)
async def verify_evidence(
    payload: VerificationCreate,
    current_user: AuthenticatedUser = Depends(require_role([UserRole.EMPLOYER, UserRole.ADMIN])),
    verification_service: VerificationService = Depends(get_verification_service),
) -> VerificationPublic:
    verification = await verification_service.verify_evidence(
        verifier_user=current_user,
        data=payload,
    )
    return VerificationPublic.model_validate(verification)


@router.get(
    "/evidence/{evidence_id}",
    response_model=list[VerificationPublic],
    status_code=status.HTTP_200_OK,
    summary="Get verification audit trail for evidence",
    description="Retrieves the chronological audit history of status changes and verifier decisions for a skill evidence record.",
)
async def list_evidence_verifications(
    evidence_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    verification_service: VerificationService = Depends(get_verification_service),
) -> Sequence[VerificationPublic]:
    verifications = await verification_service.list_verifications_for_evidence(
        evidence_id=evidence_id,
        current_user=current_user,
    )
    return [VerificationPublic.model_validate(v) for v in verifications]
