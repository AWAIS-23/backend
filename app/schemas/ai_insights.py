"""
app/schemas/ai_insights.py
--------------------------
Response schemas for AI-powered insight features.
"""
from pydantic import BaseModel, Field


class ChallengeHintResponse(BaseModel):
    """AI-generated hint for approaching a practical challenge."""
    challenge_id: str
    hint: str | None = Field(
        default=None,
        description="AI-generated guidance. Null when AI is unavailable.",
    )
    ai_available: bool = Field(
        default=False,
        description="Whether the AI hint was successfully generated.",
    )


class EvidenceSummaryResponse(BaseModel):
    """AI-generated summary of a learner's evidence portfolio."""
    summary: str | None = Field(
        default=None,
        description="AI-generated portfolio summary. Null when AI is unavailable.",
    )
    ai_available: bool = Field(
        default=False,
        description="Whether the AI summary was successfully generated.",
    )
    evidence_count: int = Field(
        default=0,
        description="Total number of evidence items analyzed.",
    )
