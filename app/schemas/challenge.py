import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from app.core.constants import ChallengeStatus, DifficultyLevel


class ChallengeSkillItem(BaseModel):
    skill_id: uuid.UUID
    importance_weight: float = Field(default=1.0, ge=0.0, le=1.0)


class ChallengeCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    instructions: str | None = None
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    organization_id: uuid.UUID | None = None
    role_id: uuid.UUID | None = None
    time_limit_seconds: int | None = Field(default=None, gt=0)
    submission_deadline: datetime | None = None
    status: ChallengeStatus = ChallengeStatus.DRAFT
    skills: list[ChallengeSkillItem] = Field(default_factory=list)


class ChallengeSkillPublic(BaseModel):
    skill_id: uuid.UUID
    skill_name: str
    importance_weight: float

    model_config = ConfigDict(from_attributes=True)


class ChallengePublic(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    difficulty: DifficultyLevel
    status: ChallengeStatus
    organization_id: uuid.UUID | None = None
    role_id: uuid.UUID | None = None
    time_limit_seconds: int | None = None
    submission_deadline: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChallengeDetailPublic(ChallengePublic):
    instructions: str | None = None
    skills: list[ChallengeSkillPublic] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
