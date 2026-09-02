import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.core.constants import AttemptStatus
from app.schemas.assessment import AssessmentQuestionPublic


class AttemptStartResponse(BaseModel):
    """Returned when an attempt is started; contains server timestamps and questions."""
    id: uuid.UUID
    assessment_id: uuid.UUID
    started_at: datetime
    expires_at: datetime
    status: AttemptStatus
    attempt_number: int
    questions: list[AssessmentQuestionPublic]

    model_config = ConfigDict(from_attributes=True)


class AttemptStatusResponse(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    started_at: datetime
    expires_at: datetime
    submitted_at: datetime | None = None
    status: AttemptStatus
    attempt_number: int

    model_config = ConfigDict(from_attributes=True)


class AnswerSubmitRequest(BaseModel):
    question_id: uuid.UUID = Field(..., description="ID of the question being answered")
    selected_option: str = Field(..., min_length=1, max_length=255, description="Selected option identifier, e.g. 'a'")


class AnswerSubmitResponse(BaseModel):
    """
    Receipt confirming the answer was securely recorded.
    NOTE: Does NOT return correctness or score to prevent early leakage.
    """
    id: uuid.UUID
    attempt_id: uuid.UUID
    question_id: uuid.UUID
    answered_at: datetime

    model_config = ConfigDict(from_attributes=True)
