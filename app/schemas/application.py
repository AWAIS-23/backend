import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.core.constants import ApplicationStatus


class ApplicationCreate(BaseModel):
    cover_note: str | None = Field(default=None, max_length=5000)


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus = Field(
        ...,
        description="Target status (submitted, reviewing, shortlisted, rejected, accepted, withdrawn)",
    )


class ApplicationPublic(BaseModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    profile_id: uuid.UUID
    status: ApplicationStatus
    cover_note: str | None = None
    applied_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
