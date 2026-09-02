import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class SkillBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_skill_id: uuid.UUID | None = None
    category: str = Field(..., min_length=1, max_length=100)


class SkillCreate(SkillBase):
    pass


class SkillResponse(SkillBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SkillWithChildrenResponse(SkillResponse):
    children: list[SkillResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
