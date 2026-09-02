import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from app.core.constants import AssessmentStatus, DifficultyLevel, QuestionType
from app.schemas.skill import SkillResponse


class QuestionOption(BaseModel):
    id: str = Field(..., description="Option identifier, e.g. 'a', 'b', 'c', 'd'")
    text: str = Field(..., description="Display text for the option")


class AssessmentQuestionPublic(BaseModel):
    """
    Learner-facing question representation.
    CRITICAL SECURITY INVARIANT:
    'correct_answer', 'is_correct', and 'explanation' are strictly omitted to prevent answer leakage.
    """
    id: uuid.UUID
    question_text: str
    question_type: QuestionType
    options: list[QuestionOption]
    points: int
    display_order: int

    model_config = ConfigDict(from_attributes=True)


class AssessmentQuestionCreate(BaseModel):
    question_text: str
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    options: list[QuestionOption]
    correct_answer: str = Field(..., description="Option ID that represents the correct answer")
    points: int = 10
    display_order: int = 1
    explanation: str | None = None


class AssessmentBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    skill_id: uuid.UUID
    role_id: uuid.UUID | None = None
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    duration_seconds: int = Field(default=1800, gt=0, description="Time limit in seconds")
    passing_score: int = Field(default=70, ge=0, le=100, description="Passing percentage threshold (0-100)")


class AssessmentCreate(AssessmentBase):
    status: AssessmentStatus = AssessmentStatus.DRAFT
    questions: list[AssessmentQuestionCreate] = Field(default_factory=list)


class AssessmentPublic(AssessmentBase):
    id: uuid.UUID
    status: AssessmentStatus
    created_at: datetime
    skill: SkillResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class AssessmentDetailPublic(AssessmentPublic):
    """Assessment details including learner-safe questions."""
    questions: list[AssessmentQuestionPublic] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
