"""
Unit tests for SkillGapService.

Verifies:
- Successful AI explanation is returned with deterministic data.
- AI failure degrades gracefully (ai_explanation=null, ai_available=false).
- Deterministic data is always preserved regardless of AI outcome.
- Service NEVER recalculates scores — only reads existing Match data.
- Empty/whitespace AI responses are treated as failure.
- ResourceNotFoundException when no match exists.
- Correct deterministic data is forwarded to AIService.
"""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.exceptions import (
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)
from app.ai.schemas import AIResponse
from app.core.exceptions import ResourceNotFoundException
from app.services.skill_gap_service import SkillGapService


OPP_ID = uuid.UUID("88888888-9999-0000-1111-222233334444")
PROFILE_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MATCH_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
NOW = datetime.now(timezone.utc)


def _make_match(
    overall_score: float = 72.5,
    skill_score: float = 80.0,
    evidence_score: float = 60.0,
    experience_score: float = 50.0,
    breakdown: dict | None = None,
    opportunity_title: str = "Backend Engineer",
    opportunity_type_value: str = "job",
):
    """Build a mock Match object mimicking the SQLAlchemy model."""
    if breakdown is None:
        breakdown = {
            "matched_skills": 2,
            "required_skills": 3,
            "skill_details": [
                {
                    "skill_id": "11110000-1111-2222-3333-444455556666",
                    "skill_name": "Python",
                    "weight": 0.5,
                    "coverage": 100.0,
                    "has_verified_evidence": True,
                    "evidence_score": 100.0,
                },
                {
                    "skill_id": "22220000-1111-2222-3333-444455556666",
                    "skill_name": "FastAPI",
                    "weight": 0.3,
                    "coverage": 50.0,
                    "has_verified_evidence": False,
                    "evidence_score": 0.0,
                },
            ],
        }
    opp_type = SimpleNamespace(value=opportunity_type_value)
    opportunity = SimpleNamespace(
        title=opportunity_title,
        opportunity_type=opp_type,
    )
    return SimpleNamespace(
        id=MATCH_ID,
        opportunity_id=OPP_ID,
        profile_id=PROFILE_ID,
        overall_score=overall_score,
        skill_score=skill_score,
        evidence_score=evidence_score,
        experience_score=experience_score,
        breakdown=breakdown,
        created_at=NOW,
        opportunity=opportunity,
    )


def _make_service(
    match=None,
    ai_response: AIResponse | None = None,
    ai_error: Exception | None = None,
):
    """Build a SkillGapService with mocked dependencies."""
    mock_repo = MagicMock()
    mock_repo.get_match = AsyncMock(return_value=match)

    mock_ai = MagicMock()
    if ai_error is not None:
        mock_ai.complete = AsyncMock(side_effect=ai_error)
    else:
        mock_ai.complete = AsyncMock(
            return_value=ai_response or AIResponse(
                content="Your Python skills are strong.",
                model="fake-model",
            )
        )

    return SkillGapService(mock_repo, mock_ai), mock_repo, mock_ai


class TestSuccessfulExplanation:
    async def test_returns_ai_explanation_with_deterministic_data(self):
        svc, _, _ = _make_service(
            match=_make_match(),
            ai_response=AIResponse(
                content="You have strong Python skills but need more PostgreSQL experience.",
                model="fake-model",
            ),
        )
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        assert result.ai_explanation == (
            "You have strong Python skills but need more PostgreSQL experience."
        )
        assert result.ai_available is True
        assert result.overall_score == 72.5
        assert result.skill_score == 80.0
        assert result.evidence_score == 60.0
        assert result.experience_score == 50.0

    async def test_deterministic_fields_always_present(self):
        svc, _, _ = _make_service(match=_make_match())
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        assert result.match_id == MATCH_ID
        assert result.opportunity_id == OPP_ID
        assert result.profile_id == PROFILE_ID
        assert result.opportunity_title == "Backend Engineer"
        assert result.opportunity_type == "job"
        assert len(result.skill_details) == 2
        assert result.skill_details[0].skill_name == "Python"

    async def test_breakdown_preserved(self):
        match = _make_match()
        svc, _, _ = _make_service(match=match)
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        assert result.breakdown == match.breakdown
        assert result.breakdown["matched_skills"] == 2


class TestGracefulDegradation:
    async def test_ai_provider_error_degrades(self):
        svc, _, _ = _make_service(
            match=_make_match(),
            ai_error=AIProviderError("Provider failed"),
        )
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        assert result.ai_explanation is None
        assert result.ai_available is False
        # Deterministic data still present.
        assert result.overall_score == 72.5
        assert len(result.skill_details) == 2

    async def test_ai_timeout_degrades(self):
        svc, _, _ = _make_service(
            match=_make_match(),
            ai_error=AITimeoutError(),
        )
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        assert result.ai_explanation is None
        assert result.ai_available is False
        assert result.overall_score == 72.5

    async def test_ai_rate_limit_degrades(self):
        svc, _, _ = _make_service(
            match=_make_match(),
            ai_error=AIRateLimitError(),
        )
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        assert result.ai_explanation is None
        assert result.ai_available is False
        assert result.overall_score == 72.5

    async def test_unexpected_exception_degrades(self):
        svc, _, _ = _make_service(
            match=_make_match(),
            ai_error=RuntimeError("unexpected boom"),
        )
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        assert result.ai_explanation is None
        assert result.ai_available is False
        assert result.overall_score == 72.5

    async def test_empty_ai_response_treated_as_failure(self):
        svc, _, _ = _make_service(
            match=_make_match(),
            ai_response=AIResponse(content="", model="fake-model"),
        )
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        assert result.ai_explanation is None
        assert result.ai_available is False

    async def test_whitespace_only_ai_response_treated_as_failure(self):
        svc, _, _ = _make_service(
            match=_make_match(),
            ai_response=AIResponse(content="   \n  ", model="fake-model"),
        )
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        assert result.ai_explanation is None
        assert result.ai_available is False


class TestNoMatchFound:
    async def test_raises_resource_not_found(self):
        svc, _, _ = _make_service(match=None)

        with pytest.raises(ResourceNotFoundException):
            await svc.explain_skill_gap(OPP_ID, PROFILE_ID)


class TestServiceDoesNotRecalculateScores:
    async def test_service_reads_scores_from_match_only(self):
        """The service must pass through scores from the Match record
        without modification — no secondary computation."""
        match = _make_match(
            overall_score=42.0,
            skill_score=55.0,
            evidence_score=30.0,
            experience_score=10.0,
        )
        svc, _, _ = _make_service(match=match)
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        # Scores must match the source record exactly.
        assert result.overall_score == 42.0
        assert result.skill_score == 55.0
        assert result.evidence_score == 30.0
        assert result.experience_score == 10.0

    async def test_skill_details_from_breakdown_not_recomputed(self):
        """skill_details must come from Match.breakdown, not from any
        service-level query or computation."""
        match = _make_match()
        svc, mock_repo, _ = _make_service(match=match)
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        # Only get_match was called — no calculate, no save, no query
        # beyond the single read.
        mock_repo.get_match.assert_called_once_with(OPP_ID, PROFILE_ID)
        # No other repo methods called.
        assert len(mock_repo.method_calls) == 1


class TestAIServiceInteraction:
    async def test_ai_service_called_with_correct_feature(self):
        svc, _, mock_ai = _make_service(match=_make_match())
        await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        mock_ai.complete.assert_called_once()
        call_kwargs = mock_ai.complete.call_args
        assert call_kwargs.kwargs.get("feature") == "skill_gap_explanation"

    async def test_ai_receives_prompt_builder_not_raw_strings(self):
        """AIService.complete should receive a PromptBuilder, not raw text."""
        from app.ai.prompts.base import PromptBuilder

        svc, _, mock_ai = _make_service(match=_make_match())
        await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        prompt_arg = mock_ai.complete.call_args.args[0]
        assert isinstance(prompt_arg, PromptBuilder)

    async def test_learner_note_forwarded_to_prompt(self):
        svc, _, mock_ai = _make_service(match=_make_match())
        await svc.explain_skill_gap(OPP_ID, PROFILE_ID, learner_note="Focus on DB skills")

        mock_ai.complete.assert_called_once()
        # The PromptBuilder should contain the learner note.
        prompt_arg = mock_ai.complete.call_args.args[0]
        messages = prompt_arg.build()
        user_content = messages[1].content
        assert "Focus on DB skills" in user_content


class TestNullBreakdown:
    async def test_empty_breakdown_handled_gracefully(self):
        match = _make_match(breakdown={})
        svc, _, _ = _make_service(match=match)
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        assert result.skill_details == []
        assert result.breakdown == {}
        # AI still called (with empty skill details).
        assert result.ai_available is True

    async def test_none_breakdown_handled_gracefully(self):
        match = _make_match(breakdown=None)
        # Override breakdown to None.
        match.breakdown = None
        svc, _, _ = _make_service(match=match)
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        assert result.skill_details == []


class TestAIServiceUnavailable:
    """P2-01: When ai_service is None (AI disabled or misconfigured),
    the service must return deterministic data with ai_explanation=null."""

    async def test_none_ai_service_degrades_gracefully(self):
        """SkillGapService(ai_service=None) returns deterministic data only."""
        mock_repo = MagicMock()
        mock_repo.get_match = AsyncMock(return_value=_make_match())

        svc = SkillGapService(mock_repo, ai_service=None)
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        assert result.ai_explanation is None
        assert result.ai_available is False
        # Deterministic data intact.
        assert result.overall_score == 72.5
        assert result.skill_score == 80.0
        assert result.evidence_score == 60.0
        assert result.experience_score == 50.0
        assert result.opportunity_title == "Backend Engineer"
        assert len(result.skill_details) == 2

    async def test_none_ai_service_default_parameter(self):
        """SkillGapService(repo) without explicit ai_service also degrades."""
        mock_repo = MagicMock()
        mock_repo.get_match = AsyncMock(return_value=_make_match())

        svc = SkillGapService(mock_repo)
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        assert result.ai_explanation is None
        assert result.ai_available is False
        assert result.overall_score == 72.5

    async def test_none_ai_service_no_match_still_raises_404(self):
        """ResourceNotFoundException must fire even when AI is unavailable."""
        mock_repo = MagicMock()
        mock_repo.get_match = AsyncMock(return_value=None)

        svc = SkillGapService(mock_repo, ai_service=None)

        with pytest.raises(ResourceNotFoundException):
            await svc.explain_skill_gap(OPP_ID, PROFILE_ID)


class TestSkillIdSanitization:
    """P2-02: skill_id UUIDs must be stripped before reaching the AI provider."""

    async def test_skill_id_not_sent_to_ai(self):
        """Verify skill_id is removed from skill details before AI call."""
        svc, _, mock_ai = _make_service(match=_make_match())
        await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        mock_ai.complete.assert_called_once()
        prompt_arg = mock_ai.complete.call_args.args[0]
        messages = prompt_arg.build()
        combined = " ".join(m.content for m in messages)

        # The breakdown contains these skill_id UUIDs — they must not
        # appear in the AI prompt.
        assert "11110000-1111-2222-3333-444455556666" not in combined
        assert "22220000-1111-2222-3333-444455556666" not in combined

    async def test_skill_names_still_sent_to_ai(self):
        """skill_name and other fields must remain intact after sanitization."""
        svc, _, mock_ai = _make_service(match=_make_match())
        await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        mock_ai.complete.assert_called_once()
        prompt_arg = mock_ai.complete.call_args.args[0]
        messages = prompt_arg.build()
        combined = " ".join(m.content for m in messages)

        assert "Python" in combined
        assert "FastAPI" in combined
        assert "coverage" in combined or "100.0" in combined

    async def test_response_skill_details_retain_skill_id(self):
        """The API response SkillDetailItem must still include skill_id
        for the frontend — only the AI prompt is sanitized."""
        svc, _, _ = _make_service(match=_make_match())
        result = await svc.explain_skill_gap(OPP_ID, PROFILE_ID)

        # The response still has skill_id from the breakdown.
        assert result.skill_details[0].skill_id == "11110000-1111-2222-3333-444455556666"
        assert result.skill_details[1].skill_id == "22220000-1111-2222-3333-444455556666"
