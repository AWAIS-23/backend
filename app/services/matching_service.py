import math
import uuid
import logging
from typing import Sequence
from app.core.constants import EvidenceSourceType, EvidenceStatus, OrgRole, UserRole
from app.core.exceptions import (
    PermissionDeniedException,
    ResourceNotFoundException,
)
from app.core.security import AuthenticatedUser
from app.models.match import Match
from app.repositories.evidence_repo import EvidenceRepository
from app.repositories.matching_repo import MatchingRepository
from app.repositories.opportunity_repo import OpportunityRepository
from app.repositories.submission_repo import SubmissionRepository
from app.schemas.common import PaginatedResponse
from app.schemas.match import MatchPublic

logger = logging.getLogger("rising_skills.services.matching")


class MatchingService:
    def __init__(
        self,
        matching_repo: MatchingRepository,
        opportunity_repo: OpportunityRepository,
        evidence_repo: EvidenceRepository,
        submission_repo: SubmissionRepository,
    ):
        self.matching_repo = matching_repo
        self.opportunity_repo = opportunity_repo
        self.evidence_repo = evidence_repo
        self.submission_repo = submission_repo

    async def calculate_and_save_match(
        self,
        opportunity_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> Match:
        opportunity = await self.opportunity_repo.get_with_skills(opportunity_id)
        if not opportunity:
            raise ResourceNotFoundException(resource="Opportunity", identifier=opportunity_id)

        evidence_items, _ = await self.evidence_repo.list_for_profile(
            profile_id=profile_id,
            skip=0,
            limit=1000,
        )

        required_skills = opportunity.opportunity_skills
        req_count = len(required_skills)

        # 1. Deterministic Skill Score (Weighted average of verified skill coverage)
        total_weight = 0.0
        weighted_coverage = 0.0
        skill_details = []
        matched_verified_count = 0

        for os in required_skills:
            weight = os.importance_weight
            total_weight += weight
            skill_name = os.skill.name if os.skill else "Unknown Skill"

            # Filter for learner's VERIFIED evidence for this skill
            verified_matches = [
                e for e in evidence_items
                if e.skill_id == os.skill_id and e.status == EvidenceStatus.VERIFIED
            ]

            if verified_matches:
                has_verified = True
                best_score = max(e.score for e in verified_matches)
                coverage = min(100.0, best_score)
                matched_verified_count += 1
            else:
                has_verified = False
                coverage = 0.0
                best_score = 0.0

            weighted_coverage += weight * coverage
            skill_details.append({
                "skill_id": str(os.skill_id),
                "skill_name": skill_name,
                "weight": weight,
                "coverage": round(coverage, 2),
                "has_verified_evidence": has_verified,
                "evidence_score": round(best_score, 2),
            })

        skill_score = (
            round(weighted_coverage / total_weight, 2)
            if total_weight > 0
            else 0.0
        )

        # 2. Evidence Score (Ratio of verified required skills)
        evidence_score = (
            round((matched_verified_count / req_count) * 100.0, 2)
            if req_count > 0
            else 0.0
        )

        # 3. Experience Score (Based on verified practical challenge demonstrations)
        verified_challenges_count = sum(
            1 for e in evidence_items
            if e.source_type == EvidenceSourceType.CHALLENGE_SUBMISSION
            and e.status == EvidenceStatus.VERIFIED
        )
        if verified_challenges_count >= 2:
            experience_score = 100.0
        elif verified_challenges_count == 1:
            experience_score = 70.0
        else:
            experience_score = 0.0

        # 4. Deterministic Overall Composite Score
        # Formula: 60% Skill Score + 30% Evidence Score + 10% Experience Score
        overall_score = round(
            0.60 * skill_score + 0.30 * evidence_score + 0.10 * experience_score,
            2,
        )

        breakdown = {
            "matched_skills": matched_verified_count,
            "required_skills": req_count,
            "skill_details": skill_details,
            "verified_challenges_count": verified_challenges_count,
            "formula": "0.60*skill_score + 0.30*evidence_score + 0.10*experience_score",
        }

        match = await self.matching_repo.save_or_update_match(
            opportunity_id=opportunity_id,
            profile_id=profile_id,
            overall_score=overall_score,
            skill_score=skill_score,
            evidence_score=evidence_score,
            experience_score=experience_score,
            breakdown=breakdown,
        )

        logger.info(
            f"Match calculated for profile '{profile_id}' on opportunity '{opportunity_id}': "
            f"Overall {overall_score}% (Skill: {skill_score}, Evidence: {evidence_score}, Exp: {experience_score})"
        )
        return match

    async def list_matches_for_opportunity(
        self,
        opportunity_id: uuid.UUID,
        current_user: AuthenticatedUser,
        min_score: float = 0.0,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[MatchPublic]:
        opportunity = await self.opportunity_repo.get_by_id(opportunity_id)
        if not opportunity:
            raise ResourceNotFoundException(resource="Opportunity", identifier=opportunity_id)

        # RBAC: Employer in organization or Admin
        if current_user.role != UserRole.ADMIN:
            org_role = current_user.org_roles.get(str(opportunity.organization_id))
            if current_user.role != UserRole.EMPLOYER or org_role not in [OrgRole.OWNER, OrgRole.ADMIN, OrgRole.RECRUITER, OrgRole.EVALUATOR]:
                raise PermissionDeniedException("You are not authorized to view candidate matches for this opportunity.")

        skip = (page - 1) * page_size
        items, total = await self.matching_repo.list_matches_for_opportunity(
            opportunity_id=opportunity_id,
            min_score=min_score,
            skip=skip,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse[MatchPublic](
            items=[MatchPublic.model_validate(m) for m in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def list_matches_for_learner(
        self,
        profile_id: uuid.UUID,
        current_user: AuthenticatedUser,
        min_score: float = 0.0,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[MatchPublic]:
        user_uuid = uuid.UUID(current_user.id)
        if current_user.role != UserRole.ADMIN and profile_id != user_uuid:
            raise PermissionDeniedException("You are not authorized to view matches for another learner profile.")

        skip = (page - 1) * page_size
        items, total = await self.matching_repo.list_matches_for_profile(
            profile_id=profile_id,
            min_score=min_score,
            skip=skip,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse[MatchPublic](
            items=[MatchPublic.model_validate(m) for m in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
