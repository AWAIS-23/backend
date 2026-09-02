import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ExperienceFeedbackCreate(BaseModel):
    overall_rating: int = Field(..., ge=1, le=5, description="Overall performance rating (1-5)")
    strengths: str | None = Field(default=None, max_length=5000)
    areas_for_improvement: str | None = Field(default=None, max_length=5000)
    communication_rating: int | None = Field(default=None, ge=1, le=5)
    technical_rating: int | None = Field(default=None, ge=1, le=5)
    problem_solving_rating: int | None = Field(default=None, ge=1, le=5)
    teamwork_rating: int | None = Field(default=None, ge=1, le=5)
    professionalism_rating: int | None = Field(default=None, ge=1, le=5)
    recommendation: str | None = Field(default=None, max_length=2000)


class ExperienceFeedbackPublic(BaseModel):
    id: uuid.UUID
    experience_id: uuid.UUID
    profile_id: uuid.UUID
    organization_id: uuid.UUID
    reviewer_id: uuid.UUID
    overall_rating: int
    strengths: str | None = None
    areas_for_improvement: str | None = None
    communication_rating: int | None = None
    technical_rating: int | None = None
    problem_solving_rating: int | None = None
    teamwork_rating: int | None = None
    professionalism_rating: int | None = None
    recommendation: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
