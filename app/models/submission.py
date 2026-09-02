import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.constants import SubmissionStatus
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.challenge import Challenge
    from app.models.evaluation import Evaluation
    from app.models.profile import Profile


class Submission(Base, TimestampMixin):
    """
    A learner's practical work submission against a specific challenge.
    Ownership is established via profile_id, always derived from the JWT.
    """
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("challenges.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    repository_url: Mapped[str | None] = mapped_column(
        String(2048), nullable=True,
        doc="Link to code repository (GitHub, GitLab, etc.)"
    )
    deployment_url: Mapped[str | None] = mapped_column(
        String(2048), nullable=True,
        doc="Link to live deployment or demo"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        doc="Learner's written explanation of their approach and decisions"
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        SQLEnum(SubmissionStatus, name="submission_status_enum", native_enum=False),
        nullable=False,
        default=SubmissionStatus.DRAFT,
        index=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        doc="Timestamp when learner officially submitted (status → submitted)"
    )

    # Relationships
    challenge: Mapped["Challenge"] = relationship(
        "Challenge", back_populates="submissions", lazy="joined"
    )
    submitter: Mapped["Profile"] = relationship("Profile", lazy="joined")
    evaluations: Mapped[list["Evaluation"]] = relationship(
        "Evaluation",
        back_populates="submission",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
