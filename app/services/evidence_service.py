import math
import uuid
import logging
from app.core.constants import EvidenceSourceType, EvidenceStatus, UserRole
from app.core.exceptions import PermissionDeniedException, ResourceNotFoundException
from app.core.security import AuthenticatedUser
from app.models.evidence import Evidence
from app.repositories.evidence_repo import EvidenceRepository
from app.schemas.common import PaginatedResponse
from app.schemas.evidence import EvidencePublic

logger = logging.getLogger("rising_skills.services.evidence")


class EvidenceService:
    def __init__(self, evidence_repo: EvidenceRepository):
        self.evidence_repo = evidence_repo

    async def list_profile_evidence(
        self,
        profile_id: uuid.UUID,
        current_user: AuthenticatedUser,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[EvidencePublic]:
        user_uuid = uuid.UUID(current_user.id)
        is_owner = profile_id == user_uuid
        is_privileged = current_user.role in [UserRole.ADMIN, UserRole.EMPLOYER]

        if not (is_owner or is_privileged):
            raise PermissionDeniedException("You are not authorized to view evidence for this profile.")

        skip = (page - 1) * page_size
        items, total = await self.evidence_repo.list_for_profile(
            profile_id=profile_id,
            skip=skip,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse[EvidencePublic](
            items=[EvidencePublic.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_evidence_detail(
        self,
        evidence_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> Evidence:
        evidence = await self.evidence_repo.get_with_verifications(evidence_id)
        if not evidence:
            raise ResourceNotFoundException(resource="Evidence", identifier=evidence_id)

        user_uuid = uuid.UUID(current_user.id)
        is_owner = evidence.profile_id == user_uuid
        is_privileged = current_user.role in [UserRole.ADMIN, UserRole.EMPLOYER]

        if not (is_owner or is_privileged):
            raise PermissionDeniedException("You are not authorized to view this evidence record.")

        return evidence

    async def create_self_reported_claim(
        self,
        profile_id: uuid.UUID,
        skill_id: uuid.UUID,
        proficiency: str | None = None,
        notes: str | None = None,
    ) -> Evidence:
        """
        Creates a self-reported skill claim by the learner (a profile-level claim,
        not derived from any assessment or submission). Status starts as UNVERIFIED
        and can only move forward through the human verification workflow.
        """
        existing = await self.evidence_repo.find_self_reported(
            profile_id=profile_id,
            skill_id=skill_id,
        )
        if existing:
            return existing

        evidence = Evidence(
            profile_id=profile_id,
            skill_id=skill_id,
            source_type=EvidenceSourceType.SELF_REPORTED,
            source_id=profile_id,
            score=0.0,
            evidence_data={
                "self_reported": True,
                "proficiency": proficiency,
                "notes": notes,
            },
            status=EvidenceStatus.UNVERIFIED,
        )
        created = await self.evidence_repo.create(evidence)
        logger.info(f"Self-reported skill claim '{created.id}' created for user '{profile_id}' (Skill: '{skill_id}').")
        return created

    async def create_assessment_evidence(
        self,
        profile_id: uuid.UUID,
        skill_id: uuid.UUID,
        assessment_result_id: uuid.UUID,
        score: float,
        passed: bool,
    ) -> Evidence:
        """
        Creates evidence originating from a passed/completed knowledge assessment.
        """
        existing = await self.evidence_repo.find_by_source(
            source_type=EvidenceSourceType.ASSESSMENT.value,
            source_id=assessment_result_id,
            profile_id=profile_id,
        )
        if existing:
            return existing

        evidence = Evidence(
            profile_id=profile_id,
            skill_id=skill_id,
            source_type=EvidenceSourceType.ASSESSMENT,
            source_id=assessment_result_id,
            score=score,
            evidence_data={"assessment_result_id": str(assessment_result_id), "passed": passed},
            status=EvidenceStatus.VERIFIED if passed else EvidenceStatus.UNVERIFIED,
        )
        created = await self.evidence_repo.create(evidence)
        logger.info(f"Assessment evidence '{created.id}' created for user '{profile_id}' (Skill: '{skill_id}').")
        return created
