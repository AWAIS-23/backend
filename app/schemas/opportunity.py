import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.core.constants import OpportunityStatus, OpportunityType


class OpportunitySkillItem(BaseModel):
    skill_id: uuid.UUID
    importance_weight: float = Field(default=1.0, ge=0.0, le=1.0)


class OpportunitySkillPublic(BaseModel):
    skill_id: uuid.UUID
    skill_name: str
    importance_weight: float

    model_config = ConfigDict(from_attributes=True)


class OpportunityCreate(BaseModel):
    organization_id: uuid.UUID
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    opportunity_type: OpportunityType = OpportunityType.JOB
    location: str | None = None
    is_remote: bool = False
    deadline: datetime | None = None
    skills: list[OpportunitySkillItem] = Field(default_factory=list)


class OpportunityUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = None
    opportunity_type: OpportunityType | None = None
    location: str | None = None
    is_remote: bool | None = None
    deadline: datetime | None = None


class OpportunityPublic(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    description: str | None = None
    opportunity_type: OpportunityType
    status: OpportunityStatus
    location: str | None = None
    is_remote: bool
    deadline: datetime | None = None
    published_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OpportunityDetailPublic(OpportunityPublic):
    skills: list[OpportunitySkillPublic] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
