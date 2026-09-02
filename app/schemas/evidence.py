import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict
from app.core.constants import EvidenceSourceType, EvidenceStatus


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
