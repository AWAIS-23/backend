import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.core.constants import OrgRole
from app.schemas.profile import ProfileResponse


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    website_url: str | None = Field(default=None, max_length=1024)
    logo_url: str | None = Field(default=None, max_length=1024)


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationResponse(OrganizationBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationMemberResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    profile_id: uuid.UUID
    org_role: OrgRole
    created_at: datetime
    profile: ProfileResponse | None = None

    model_config = ConfigDict(from_attributes=True)
