import uuid
import logging
from typing import Sequence
from app.core.constants import ErrorCode, EvidenceStatus, UserRole
from app.core.exceptions import (
    AppException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from app.core.security import AuthenticatedUser
from app.models.verification import Verification
from app.repositories.evidence_repo import EvidenceRepository
from app.repositories.verification_repo import VerificationRepository
from app.schemas.verification import VerificationCreate

logger = logging.getLogger("rising_skills.services.verification")

ALLOWED_TRANSITIONS: dict[EvidenceStatus, set[EvidenceStatus]] = {
    EvidenceStatus.UNVERIFIED: {EvidenceStatus.PENDING},
    EvidenceStatus.PENDING: {EvidenceStatus.VERIFIED, EvidenceStatus.REJECTED},
    EvidenceStatus.VERIFIED: set(),  # Immutable once verified
    EvidenceStatus.REJECTED: set(),  # Finalized unless administrative reset
}


class VerificationService:
    def __init__(
        self,
        verification_repo: VerificationRepository,
        evidence_repo: EvidenceRepository,
    ):
        self.verification_repo = verification_repo
        self.evidence_repo = evidence_repo

    async def verify_evidence(
        self,
        verifier_user: AuthenticatedUser,
        data: VerificationCreate,
    ) -> Verification:
        verifier_uuid = uuid.UUID(verifier_user.id)

        # RBAC: Only authorized employers and admins can act as verifiers
        if verifier_user.role not in [UserRole.ADMIN, UserRole.EMPLOYER]:
            raise PermissionDeniedException("Only authorized verifiers, employers, or admins can verify evidence.")

        evidence = await self.evidence_repo.get_by_id(data.evidence_id)
        if not evidence:
            raise ResourceNotFoundException(resource="Evidence", identifier=data.evidence_id)

        # Self-Verification Guard: Learner cannot verify their own evidence
        if evidence.profile_id == verifier_uuid:
            raise AppException(
                status_code=403,
                error_code=ErrorCode.SELF_VERIFICATION_FORBIDDEN,
                message="You cannot verify your own evidence.",
            )

        current_status = EvidenceStatus(evidence.status)
        target_status = data.to_status

        # Verification State Machine Validation
        allowed_targets = ALLOWED_TRANSITIONS.get(current_status, set())
        if target_status not in allowed_targets:
            raise AppException(
                status_code=400,
                error_code=ErrorCode.INVALID_STATE_TRANSITION,
                message=f"Invalid state transition from '{current_status.value}' to '{target_status.value}'.",
            )

        # Record immutable verification audit log
        verification_entry = Verification(
            evidence_id=evidence.id,
            verifier_id=verifier_uuid,
            from_status=current_status.value,
            to_status=target_status.value,
            notes=data.notes,
        )
        created_verification = await self.verification_repo.create(verification_entry)

        # Update evidence status
        evidence.status = target_status
        await self.evidence_repo.session.flush()

        logger.info(
            f"Evidence '{evidence.id}' transitioned from '{current_status.value}' to '{target_status.value}' "
            f"by verifier '{verifier_uuid}'."
        )
        return created_verification

    async def list_verifications_for_evidence(
        self,
        evidence_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> Sequence[Verification]:
        evidence = await self.evidence_repo.get_by_id(evidence_id)
        if not evidence:
            raise ResourceNotFoundException(resource="Evidence", identifier=evidence_id)

        user_uuid = uuid.UUID(current_user.id)
        is_owner = evidence.profile_id == user_uuid
        is_privileged = current_user.role in [UserRole.ADMIN, UserRole.EMPLOYER]

        if not (is_owner or is_privileged):
            raise PermissionDeniedException("You are not authorized to view verifications for this evidence.")

        return await self.verification_repo.list_for_evidence(evidence_id)
