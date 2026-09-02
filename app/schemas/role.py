import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.skill import SkillResponse


class RoleBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str | None = None


class RoleCreate(RoleBase):
    pass


class RoleResponse(RoleBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleSkillItemResponse(BaseModel):
    id: uuid.UUID
    role_id: uuid.UUID
    skill_id: uuid.UUID
    importance_weight: float = Field(..., ge=0.0, le=1.0)
    skill: SkillResponse

    model_config = ConfigDict(from_attributes=True)


class RoleWithSkillsResponse(RoleResponse):
    role_skills: list[RoleSkillItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
