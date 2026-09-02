import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RubricItem(BaseModel):
    """A single graded criterion in the evaluation rubric."""
    criterion: str = Field(..., min_length=1, max_length=255)
    max_points: int = Field(..., ge=1, le=100)
    awarded_points: int = Field(..., ge=0)

    @model_validator(mode="after")
    def awarded_cannot_exceed_max(self) -> "RubricItem":
        if self.awarded_points > self.max_points:
            raise ValueError(
                f"awarded_points ({self.awarded_points}) cannot exceed "
                f"max_points ({self.max_points}) for criterion '{self.criterion}'."
            )
        return self


class EvaluationCreate(BaseModel):
    rubric: list[RubricItem] = Field(
        ...,
        min_length=1,
        description="At least one rubric criterion is required.",
    )
    feedback: str | None = None

    # NOTE: 'score' is intentionally NOT accepted from the client.
    # The backend calculates it from the rubric items.


class EvaluationPublic(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    evaluator_id: uuid.UUID
    rubric: list[dict]
    score: float
    feedback: str | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
