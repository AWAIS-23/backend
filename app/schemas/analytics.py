import uuid
from pydantic import BaseModel, ConfigDict


class OrganizationAnalytics(BaseModel):
    organization_id: uuid.UUID
    total_opportunities: int
    published_opportunities: int
    total_applications: int
    shortlisted_applications: int
    accepted_applications: int
    active_experiences: int
    completed_experiences: int
    verified_experiences: int
    average_match_score: float
    average_feedback_rating: float

    model_config = ConfigDict(from_attributes=True)
