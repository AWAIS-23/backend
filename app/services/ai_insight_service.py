"""
app/services/ai_insight_service.py
----------------------------------
AIInsightService — handles AI-powered features for challenges and evidence.

Architecture follows the same pattern as SkillGapService:
- Read-only with respect to domain data.
- AI output is narrative enhancement, not authoritative decisions.
- Graceful degradation: deterministic data always returned, AI fields null on failure.
"""
import logging
import uuid

from app.ai.exceptions import AIProviderError
from app.ai.prompts.challenge_hint import build_challenge_hint_prompt
from app.ai.prompts.evidence_summary import build_evidence_summary_prompt
from app.ai.service import AIService
from app.core.exceptions import ResourceNotFoundException
from app.repositories.challenge_repo import ChallengeRepository
from app.repositories.evidence_repo import EvidenceRepository
from app.repositories.skill_repo import SkillRepository
from app.schemas.ai_insights import ChallengeHintResponse, EvidenceSummaryResponse

logger = logging.getLogger("rising_skills.services.ai_insight")


class AIInsightService:
    """
    Provides AI-powered insights for challenges and evidence portfolios.
    Degrades gracefully when AI is unavailable.
    """

    def __init__(
        self,
        challenge_repo: ChallengeRepository,
        evidence_repo: EvidenceRepository,
        skill_repo: SkillRepository,
        ai_service: AIService | None = None,
    ) -> None:
        self.challenge_repo = challenge_repo
        self.evidence_repo = evidence_repo
        self.skill_repo = skill_repo
        self.ai_service = ai_service

    async def get_challenge_hint(
        self,
        challenge_id: uuid.UUID,
        learner_note: str | None = None,
    ) -> ChallengeHintResponse:
        """Generate an AI hint for approaching a challenge."""
        challenge = await self.challenge_repo.get_with_skills(challenge_id)
        if not challenge:
            raise ResourceNotFoundException(
                resource="Challenge", identifier=challenge_id
            )

        skills = [
            cs.skill.name if cs.skill else "Unknown"
            for cs in challenge.challenge_skills
        ]

        hint = await self._generate_hint(
            challenge_title=challenge.title,
            challenge_description=challenge.description,
            challenge_instructions=challenge.instructions,
            difficulty=challenge.difficulty.value if hasattr(challenge.difficulty, "value") else str(challenge.difficulty),
            skills=skills,
            learner_note=learner_note,
        )

        return ChallengeHintResponse(
            challenge_id=str(challenge_id),
            hint=hint,
            ai_available=hint is not None,
        )

    async def get_evidence_summary(
        self,
        profile_id: uuid.UUID,
        learner_note: str | None = None,
    ) -> EvidenceSummaryResponse:
        """Generate an AI summary of a learner's evidence portfolio."""
        evidence_items, _ = await self.evidence_repo.list_for_profile(
            profile_id, skip=0, limit=100
        )

        if not evidence_items:
            return EvidenceSummaryResponse(
                summary=None,
                ai_available=False,
                evidence_count=0,
            )

        # Collect skill names
        skill_ids = {e.skill_id for e in evidence_items}
        skill_names: dict[str, str] = {}
        for sid in skill_ids:
            skill = await self.skill_repo.get_by_id(sid)
            if skill:
                skill_names[str(sid)] = skill.name

        evidence_data = [
            {
                "skill_id": str(e.skill_id),
                "source_type": e.source_type.value if hasattr(e.source_type, "value") else str(e.source_type),
                "status": e.status.value if hasattr(e.status, "value") else str(e.status),
                "score": e.score,
            }
            for e in evidence_items
        ]

        summary = await self._generate_summary(
            evidence_items=evidence_data,
            skill_names=skill_names,
            learner_note=learner_note,
        )

        return EvidenceSummaryResponse(
            summary=summary,
            ai_available=summary is not None,
            evidence_count=len(evidence_items),
        )

    async def _generate_hint(
        self,
        challenge_title: str,
        challenge_description: str | None,
        challenge_instructions: str | None,
        difficulty: str,
        skills: list[str],
        learner_note: str | None,
    ) -> str | None:
        if self.ai_service is None:
            logger.info("AI service not available — returning no hint")
            return None

        try:
            prompt = build_challenge_hint_prompt(
                challenge_title=challenge_title,
                challenge_description=challenge_description,
                challenge_instructions=challenge_instructions,
                difficulty=difficulty,
                skills=skills,
                learner_note=learner_note,
            )
            response = await self.ai_service.complete(
                prompt, feature="challenge_hint"
            )
            if response.content and response.content.strip():
                return response.content.strip()
            logger.warning("AI returned empty hint")
            return None
        except AIProviderError as exc:
            logger.warning(
                f"AI hint unavailable [feature=challenge_hint] "
                f"error={getattr(exc, 'error_code', type(exc).__name__)}"
            )
            return None
        except Exception as exc:
            logger.warning(f"Unexpected error generating hint: {type(exc).__name__}")
            return None

    async def _generate_summary(
        self,
        evidence_items: list[dict],
        skill_names: dict[str, str],
        learner_note: str | None,
    ) -> str | None:
        if self.ai_service is None:
            logger.info("AI service not available — returning no summary")
            return None

        try:
            prompt = build_evidence_summary_prompt(
                evidence_items=evidence_items,
                skill_names=skill_names,
                learner_note=learner_note,
            )
            response = await self.ai_service.complete(
                prompt, feature="evidence_summary"
            )
            if response.content and response.content.strip():
                return response.content.strip()
            logger.warning("AI returned empty summary")
            return None
        except AIProviderError as exc:
            logger.warning(
                f"AI summary unavailable [feature=evidence_summary] "
                f"error={getattr(exc, 'error_code', type(exc).__name__)}"
            )
            return None
        except Exception as exc:
            logger.warning(f"Unexpected error generating summary: {type(exc).__name__}")
            return None
