import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class AssessmentResultResponse(BaseModel):
    """
    Immutable outcome report of an evaluated assessment attempt.
    """
    id: uuid.UUID
    attempt_id: uuid.UUID
    assessment_id: uuid.UUID
    assessment_title: str
    total_questions: int
    answered_questions: int
    correct_answers: int
    total_points: int
    earned_points: int
    score_percentage: float
    passed: bool
    passing_score: int
    evaluated_at: datetime
    breakdown: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
