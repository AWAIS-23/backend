import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.core.constants import ExperienceStatus, ExperienceType, VerificationStatus


class ExperienceCreate(BaseModel):
    profile_id: uuid.UUID
    organization_id: uuid.UUID | None = None
    opportunity_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    experience_type: ExperienceType = ExperienceType.INTERNSHIP
    started_at: datetime | None = None


class ExperienceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = None
    ended_at: datetime | None = None


class ExperiencePublic(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    organization_id: uuid.UUID | None = None
    opportunity_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    experience_type: ExperienceType
    started_at: datetime
    ended_at: datetime | None = None
    status: ExperienceStatus
    verification_status: VerificationStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
