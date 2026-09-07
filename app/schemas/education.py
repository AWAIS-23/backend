import uuid
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class EducationCreate(BaseModel):
    degree: str = Field(..., min_length=1, max_length=255)
    institution: str = Field(..., min_length=1, max_length=255)
    field_of_study: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    grade: str | None = Field(default=None, max_length=50)
    description: str | None = None


class EducationUpdate(BaseModel):
    degree: str | None = Field(default=None, min_length=1, max_length=255)
    institution: str | None = Field(default=None, min_length=1, max_length=255)
    field_of_study: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    grade: str | None = Field(default=None, max_length=50)
    description: str | None = None


class EducationPublic(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    degree: str
    institution: str
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    grade: str | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
