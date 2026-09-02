import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.core.constants import SubmissionStatus


class SubmissionCreate(BaseModel):
    repository_url: str | None = Field(default=None, max_length=2048)
    deployment_url: str | None = Field(default=None, max_length=2048)
    description: str | None = None


class SubmissionUpdate(BaseModel):
    repository_url: str | None = Field(default=None, max_length=2048)
    deployment_url: str | None = Field(default=None, max_length=2048)
    description: str | None = None


class SubmissionPublic(BaseModel):
    id: uuid.UUID
    challenge_id: uuid.UUID
    profile_id: uuid.UUID
    repository_url: str | None = None
    deployment_url: str | None = None
    description: str | None = None
    status: SubmissionStatus
    submitted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
