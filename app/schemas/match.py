import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class SkillMatchDetail(BaseModel):
    skill_id: uuid.UUID
    skill_name: str
    weight: float
    coverage: float
    has_verified_evidence: bool
    evidence_score: float


class MatchPublic(BaseModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    profile_id: uuid.UUID
    overall_score: float
    skill_score: float
    evidence_score: float
    experience_score: float
    breakdown: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
