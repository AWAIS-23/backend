"""
app/schemas/skill_gap.py
------------------------
Response schema for the AI Skill Gap Explanation feature (Phase 6B).

Preserves the full deterministic Match data as the authoritative payload
and adds the AI-generated explanation as an optional enhancement.

When AI is unavailable or fails, ``ai_explanation`` is null and
``ai_available`` is false — the deterministic fields remain valid.
"""
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SkillDetailItem(BaseModel):
    """A single skill from the deterministic match breakdown."""
    skill_id: str
    skill_name: str
    status: Literal["strong", "weak", "missing"] = "missing"
    weight: float
    coverage: float
    has_verified_evidence: bool
    evidence_score: float


class SkillGapExplanationResponse(BaseModel):
    """
    Full skill-gap explanation response.

    The deterministic fields (scores, skill_details, breakdown) are always
    present and authoritative. The ``ai_explanation`` is an optional
    enhancement that may be null when AI generation fails or is disabled.
    """

    # Deterministic Match fields (source of truth)
    match_id: uuid.UUID = Field(..., description="ID of the underlying Match record")
    opportunity_id: uuid.UUID
    profile_id: uuid.UUID
    overall_score: float = Field(ge=0.0, le=100.0)
    skill_score: float = Field(ge=0.0, le=100.0)
    evidence_score: float = Field(ge=0.0, le=100.0)
    experience_score: float = Field(ge=0.0, le=100.0)
    opportunity_title: str = Field(default="", description="Human-readable opportunity title")
    opportunity_type: str = Field(default="", description="Opportunity type (job, internship, etc.)")
    skill_details: list[SkillDetailItem] = Field(
        default_factory=list,
        description="Per-skill deterministic breakdown from Match.breakdown",
    )
    breakdown: dict[str, Any] = Field(
        default_factory=dict,
        description="Full Match.breakdown JSON for advanced consumers",
    )
    match_created_at: datetime

    # AI enhancement (nullable)
    ai_explanation: str | None = Field(
        default=None,
        description="AI-generated narrative explaining the skill gap. Null when AI is unavailable.",
    )
    ai_available: bool = Field(
        default=False,
        description="Whether the AI explanation was successfully generated.",
    )

    model_config = ConfigDict(from_attributes=False)
