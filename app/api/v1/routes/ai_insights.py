"""
app/api/v1/routes/ai_insights.py
---------------------------------
AI-powered insight routes for Phase 6B — Skill Gap Explanation,
Challenge Hints, and Evidence Summaries.

Follows the existing Rising Skills route conventions:
- APIRouter with prefix and tags
- Depends(get_current_user) for authentication
- Depends(get_X_service) for service injection
- Standard RFC-7807 error responses via AppException hierarchy
"""
import logging
import uuid

from fastapi import APIRouter, Depends, Query, status

from app.core.exceptions import AuthenticationRequiredException, ResourceNotFoundException
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.services import (
    get_ai_insight_service,
    get_matching_service,
    get_profile_service,
    get_skill_gap_service,
)
from app.schemas.ai_insights import ChallengeHintResponse, EvidenceSummaryResponse
from app.schemas.skill_gap import SkillGapExplanationResponse
from app.services.ai_insight_service import AIInsightService
from app.services.matching_service import MatchingService
from app.services.profile_service import ProfileService
from app.services.skill_gap_service import SkillGapService

logger = logging.getLogger("rising_skills.api.ai_insights")
router = APIRouter(prefix="/ai", tags=["AI Insights"])


@router.get(
    "/skill-gap-explanation/{opportunity_id}",
    response_model=SkillGapExplanationResponse,
    status_code=status.HTTP_200_OK,
    summary="AI skill gap explanation",
    description=(
        "Returns the deterministic match/skill-gap data for the authenticated "
        "learner and the specified opportunity, enhanced with an AI-generated "
        "narrative explanation when available. AI failure degrades gracefully — "
        "deterministic data is always returned."
    ),
)
async def get_skill_gap_explanation(
    opportunity_id: uuid.UUID,
    learner_note: str | None = Query(
        default=None,
        max_length=500,
        description="Optional focus area or preference from the learner.",
    ),
    current_user: AuthenticatedUser = Depends(get_current_user),
    matching_service: MatchingService = Depends(get_matching_service),
    profile_service: ProfileService = Depends(get_profile_service),
    skill_gap_service: SkillGapService = Depends(get_skill_gap_service),
) -> SkillGapExplanationResponse:
    try:
        profile_id = uuid.UUID(current_user.id)
    except (ValueError, TypeError):
        raise AuthenticationRequiredException("Invalid user ID in token.")

    # Ensure profile row exists to prevent FK violation on match insertion
    try:
        await profile_service.get_or_initialize_profile(
            profile_id=profile_id,
            default_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            seed_full_name=current_user.full_name,
            seed_avatar_url=current_user.avatar_url,
        )
    except Exception as exc:
        logger.warning(f"Could not verify/initialize profile {profile_id}: {exc}")

    # Ensure a current match exists before the read-only AI explanation
    try:
        await matching_service.calculate_and_save_match(
            opportunity_id=opportunity_id,
            profile_id=profile_id,
        )
    except ResourceNotFoundException:
        raise
    except Exception as exc:
        logger.warning(f"Could not auto-calculate match for opportunity {opportunity_id}: {exc}")

    return await skill_gap_service.explain_skill_gap(
        opportunity_id=opportunity_id,
        profile_id=profile_id,
        learner_note=learner_note,
    )


@router.get(
    "/challenge-hint/{challenge_id}",
    response_model=ChallengeHintResponse,
    status_code=status.HTTP_200_OK,
    summary="AI challenge hint",
    description=(
        "Returns an AI-generated hint to help the learner approach a practical "
        "challenge. Provides conceptual guidance without revealing solutions. "
        "AI failure degrades gracefully — hint is null when unavailable."
    ),
)
async def get_challenge_hint(
    challenge_id: uuid.UUID,
    learner_note: str | None = Query(
        default=None,
        max_length=500,
        description="Optional question or focus area from the learner.",
    ),
    current_user: AuthenticatedUser = Depends(get_current_user),
    ai_insight_service: AIInsightService = Depends(get_ai_insight_service),
) -> ChallengeHintResponse:
    return await ai_insight_service.get_challenge_hint(
        challenge_id=challenge_id,
        learner_note=learner_note,
    )


@router.get(
    "/evidence-summary",
    response_model=EvidenceSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="AI evidence portfolio summary",
    description=(
        "Returns an AI-generated summary of the authenticated learner's evidence "
        "portfolio, highlighting strengths and growth areas. AI failure degrades "
        "gracefully — summary is null when unavailable."
    ),
)
async def get_evidence_summary(
    learner_note: str | None = Query(
        default=None,
        max_length=500,
        description="Optional focus area or question from the learner.",
    ),
    current_user: AuthenticatedUser = Depends(get_current_user),
    ai_insight_service: AIInsightService = Depends(get_ai_insight_service),
) -> EvidenceSummaryResponse:
    return await ai_insight_service.get_evidence_summary(
        profile_id=uuid.UUID(current_user.id),
        learner_note=learner_note,
    )
