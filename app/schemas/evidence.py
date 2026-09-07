import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from app.core.constants import EvidenceSourceType, EvidenceStatus


class SelfReportClaimCreate(BaseModel):
    skill_id: uuid.UUID = Field(..., description="Skill being claimed by the learner")
    proficiency: str | None = Field(default=None, max_length=50, description="Self-declared proficiency level")
    notes: str | None = Field(default=None, max_length=2000, description="Optional supporting notes")


class SelfReportClaimUpdate(BaseModel):
    proficiency: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=2000)


class EvidencePublic(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    skill_id: uuid.UUID
    source_type: EvidenceSourceType
    source_id: uuid.UUID
    score: float
    evidence_data: dict[str, Any]
    status: EvidenceStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
