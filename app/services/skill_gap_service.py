"""
app/services/skill_gap_service.py
----------------------------------
SkillGapService — Phase 6B AI Skill Gap Explanation feature.

Responsibility:
1. Retrieve the existing deterministic Match and its breakdown data
   (computed by MatchingService — this service NEVER recalculates scores).
2. Build a structured prompt using the skill_gap PromptBuilder.
3. Call AIService to generate a human-readable explanation.
4. Gracefully degrade: if AI fails, return deterministic data with
   ``ai_explanation = null`` and ``ai_available = false``.

ARCHITECTURAL RULE: This service is READ-ONLY with respect to domain data.
It does not compute scores, create evidence, mutate match records, or
make any deterministic decisions. The AI output is a narrative enhancement,
not an authoritative platform decision.
"""
from datetime import datetime, timezone
import logging
import uuid
from typing import Any

from app.ai.exceptions import AIProviderError
from app.ai.prompts.skill_gap import build_skill_gap_prompt
from app.ai.service import AIService
from app.core.exceptions import ResourceNotFoundException
from app.models.match import Match
from app.repositories.matching_repo import MatchingRepository
from app.schemas.skill_gap import SkillDetailItem, SkillGapExplanationResponse

logger = logging.getLogger("rising_skills.services.skill_gap")


class SkillGapService:
    """
    Reads existing deterministic Match data and generates an AI-powered
    skill gap explanation for the authenticated learner.
    """

    def __init__(
        self,
        matching_repo: MatchingRepository,
        ai_service: AIService | None = None,
    ) -> None:
        self.matching_repo = matching_repo
        self.ai_service = ai_service

    async def explain_skill_gap(
        self,
        opportunity_id: uuid.UUID,
        profile_id: uuid.UUID,
        learner_note: str | None = None,
    ) -> SkillGapExplanationResponse:
        """
        Generate a skill gap explanation for a learner's existing match.

        Args:
            opportunity_id: The opportunity whose match should be explained.
            profile_id: The authenticated learner's profile ID.
            learner_note: Optional free-text focus area from the learner.

        Returns:
            SkillGapExplanationResponse with deterministic data always present
            and ``ai_explanation`` populated when AI succeeds.

        Raises:
            ResourceNotFoundException: If no match exists for the given
                opportunity + learner combination.
        """
        # 1. Read the existing deterministic Match (never computed here).
        match = await self.matching_repo.get_match(opportunity_id, profile_id)
        if not match:
            raise ResourceNotFoundException(
                resource="Match",
                identifier=f"opportunity={opportunity_id}, profile={profile_id}",
            )

        # 2. Extract deterministic data from the Match record.
        breakdown = match.breakdown or {}
        skill_details_raw: list[dict[str, Any]] = breakdown.get("skill_details", [])

        match_summary = {
            "overall_score": match.overall_score,
            "skill_score": match.skill_score,
            "evidence_score": match.evidence_score,
            "experience_score": match.experience_score,
        }

        skill_details = [
            SkillDetailItem(
                skill_id=str(item.get("skill_id", "")),
                skill_name=str(item.get("skill_name", "Unknown Skill")),
                status=item.get("status") if item.get("status") in ("strong", "weak", "missing") else "missing",
                weight=float(item.get("weight", 0.0) or 0.0),
                coverage=float(item.get("coverage", 0.0) or 0.0),
                has_verified_evidence=bool(item.get("has_verified_evidence", False)),
                evidence_score=float(item.get("evidence_score", 0.0) or 0.0),
            )
            for item in skill_details_raw
        ]

        # 3. Extract opportunity metadata from the eagerly-loaded relationship.
        opportunity_title = ""
        opportunity_type = ""
        if match.opportunity:
            opportunity_title = match.opportunity.title or ""
            opp_type = match.opportunity.opportunity_type
            opportunity_type = opp_type.value if hasattr(opp_type, "value") else str(opp_type or "")

        # 4. Build the base deterministic response.
        response = SkillGapExplanationResponse(
            match_id=match.id,
            opportunity_id=match.opportunity_id,
            profile_id=match.profile_id,
            overall_score=max(0.0, min(100.0, float(match.overall_score or 0.0))),
            skill_score=max(0.0, min(100.0, float(match.skill_score or 0.0))),
            evidence_score=max(0.0, min(100.0, float(match.evidence_score or 0.0))),
            experience_score=max(0.0, min(100.0, float(match.experience_score or 0.0))),
            opportunity_title=opportunity_title,
            opportunity_type=opportunity_type,
            skill_details=skill_details,
            breakdown=breakdown,
            match_created_at=match.created_at or datetime.now(timezone.utc),
            ai_explanation=None,
            ai_available=False,
        )

        # 5. Attempt AI explanation — graceful degradation on any failure.
        # Sanitize skill details for AI: strip internal identifiers (P2-02).
        skill_details_for_ai = [
            {k: v for k, v in item.items() if k != "skill_id"}
            for item in skill_details_raw
        ]

        ai_explanation = await self._generate_explanation(
            match_summary=match_summary,
            skill_details=skill_details_for_ai,
            opportunity_title=opportunity_title,
            opportunity_type=opportunity_type,
            learner_note=learner_note,
        )

        if ai_explanation is not None:
            response.ai_explanation = ai_explanation
            response.ai_available = True

        return response

    async def _generate_explanation(
        self,
        match_summary: dict[str, Any],
        skill_details: list[dict[str, Any]],
        opportunity_title: str,
        opportunity_type: str,
        learner_note: str | None,
    ) -> str | None:
        """
        Call AIService to generate an explanation. Returns None on any
        AI failure or when AI is not configured, so the caller can degrade
        gracefully.
        """
        if self.ai_service is None:
            logger.info(
                "AI service not available — returning deterministic data only"
            )
            return None

        try:
            prompt = build_skill_gap_prompt(
                match_summary=match_summary,
                skill_details=skill_details,
                opportunity_title=opportunity_title,
                opportunity_type=opportunity_type,
                learner_note=learner_note,
            )

            ai_response = await self.ai_service.complete(
                prompt,
                feature="skill_gap_explanation",
            )

            # Treat empty or whitespace-only responses as failure.
            if ai_response.content and ai_response.content.strip():
                return ai_response.content.strip()

            logger.warning(
                "AI returned empty explanation for skill_gap_explanation"
            )
            return None

        except AIProviderError as exc:
            # Typed AI failure — log category, degrade gracefully.
            logger.warning(
                f"AI explanation unavailable [feature=skill_gap_explanation] "
                f"error={getattr(exc, 'error_code', type(exc).__name__)}"
            )
            return None
        except Exception as exc:
            # Unexpected failure — log and degrade.
            logger.warning(
                f"Unexpected error generating AI explanation: {type(exc).__name__}"
            )
            return None
