import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.constants import AttemptStatus
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.assessment_answer import AssessmentAnswer
    from app.models.assessment_result import AssessmentResult
    from app.models.profile import Profile


class AssessmentAttempt(Base, TimestampMixin):
    """
    Learner attempt instance on a specific assessment.
    Manages timed attempt state and answer recording.
    """
    __tablename__ = "assessment_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Server-calculated expiry timestamp: started_at + duration_seconds",
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[AttemptStatus] = mapped_column(
        SQLEnum(AttemptStatus, name="attempt_status_enum", native_enum=False),
        nullable=False,
        default=AttemptStatus.IN_PROGRESS,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="attempts",
        lazy="joined",
    )
    profile: Mapped["Profile"] = relationship(
        "Profile",
        lazy="joined",
    )
    answers: Mapped[list["AssessmentAnswer"]] = relationship(
        "AssessmentAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    result: Mapped["AssessmentResult | None"] = relationship(
        "AssessmentResult",
        back_populates="attempt",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined",
    )
