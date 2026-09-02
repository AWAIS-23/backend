import uuid
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.assessment_attempt import AssessmentAttempt


class AssessmentResult(Base, TimestampMixin):
    """
    Immutable evaluation outcome of an assessment attempt.
    """
    __tablename__ = "assessment_results"
    __table_args__ = (
        CheckConstraint(
            "score_percentage >= 0.0 AND score_percentage <= 100.0",
            name="chk_result_percentage_range",
        ),
        CheckConstraint(
            "earned_points >= 0",
            name="chk_result_earned_points_non_negative",
        ),
        CheckConstraint(
            "total_points >= 0",
            name="chk_result_total_points_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    total_questions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    answered_questions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    correct_answers: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    total_points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    earned_points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    score_percentage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Detailed breakdown by skill/question topics without leaking future answer keys.",
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    attempt: Mapped["AssessmentAttempt"] = relationship(
        "AssessmentAttempt",
        back_populates="result",
        lazy="joined",
    )
