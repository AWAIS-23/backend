import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.core.constants import EvidenceStatus


class VerificationCreate(BaseModel):
    evidence_id: uuid.UUID
    to_status: EvidenceStatus = Field(
        ...,
        description="Target status. Only 'pending', 'verified', or 'rejected' are valid transitions.",
    )
    notes: str | None = Field(default=None, max_length=2000)


class VerificationPublic(BaseModel):
    id: uuid.UUID
    evidence_id: uuid.UUID
    verifier_id: uuid.UUID
    from_status: str
    to_status: str
    notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
