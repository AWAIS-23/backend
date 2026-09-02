import uuid
from typing import Any, TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.constants import QuestionType
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.assessment import Assessment


class AssessmentQuestion(Base, TimestampMixin):
    """
    Assessment question model.
    CRITICAL: 'correct_answer' and 'explanation' must never be returned to learners before evaluation.
    """
    __tablename__ = "assessment_questions"
    __table_args__ = (
        CheckConstraint(
            "points >= 0",
            name="chk_question_points_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    question_type: Mapped[QuestionType] = mapped_column(
        SQLEnum(QuestionType, name="question_type_enum", native_enum=False),
        nullable=False,
        default=QuestionType.MULTIPLE_CHOICE,
    )
    options: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        doc="List of options, e.g. [{'id': 'a', 'text': 'Option A'}, {'id': 'b', 'text': 'Option B'}]",
    )
    correct_answer: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Internal answer key for server-side evaluation. Never leak to client.",
    )
    points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Explanation of the correct answer, revealed only after submission.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="questions",
        lazy="joined",
    )
