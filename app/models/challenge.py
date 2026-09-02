import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.constants import ChallengeStatus, DifficultyLevel
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.challenge_skill import ChallengeSkill
    from app.models.organization import Organization
    from app.models.profile import Profile
    from app.models.role import Role
    from app.models.submission import Submission


class Challenge(Base, TimestampMixin):
    """
    Practical work challenge that allows a learner to demonstrate capability.
    Can be platform-created (organization_id=None) or employer-linked.
    """
    __tablename__ = "challenges"
    __table_args__ = (
        CheckConstraint(
            "time_limit_seconds IS NULL OR time_limit_seconds > 0",
            name="chk_challenge_time_limit_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        SQLEnum(DifficultyLevel, name="difficulty_level_enum", native_enum=False),
        nullable=False,
        default=DifficultyLevel.BEGINNER,
        index=True,
    )
    status: Mapped[ChallengeStatus] = mapped_column(
        SQLEnum(ChallengeStatus, name="challenge_status_enum", native_enum=False),
        nullable=False,
        default=ChallengeStatus.DRAFT,
        index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    time_limit_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Optional time limit for submission. NULL means no limit.",
    )
    submission_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Optional hard deadline. Submissions after this timestamp are rejected.",
    )

    # Relationships
    creator: Mapped["Profile | None"] = relationship("Profile", lazy="joined")
    challenge_skills: Mapped[list["ChallengeSkill"]] = relationship(
        "ChallengeSkill",
        back_populates="challenge",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission",
        back_populates="challenge",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
