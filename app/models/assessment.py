import uuid
from typing import TYPE_CHECKING
from sqlalchemy import (
    CheckConstraint,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.constants import AssessmentStatus, DifficultyLevel
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.assessment_attempt import AssessmentAttempt
    from app.models.assessment_question import AssessmentQuestion
    from app.models.profile import Profile
    from app.models.role import Role
    from app.models.skill import Skill


class Assessment(Base, TimestampMixin):
    """
    Theoretical / knowledge-based skill assessment entity.
    """
    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "passing_score >= 0 AND passing_score <= 100",
            name="chk_assessment_passing_score",
        ),
        CheckConstraint(
            "duration_seconds > 0",
            name="chk_assessment_duration_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        SQLEnum(DifficultyLevel, name="difficulty_level_enum", native_enum=False),
        nullable=False,
        default=DifficultyLevel.BEGINNER,
        index=True,
    )
    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1800,  # 30 minutes
    )
    passing_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=70,  # 70%
    )
    status: Mapped[AssessmentStatus] = mapped_column(
        SQLEnum(AssessmentStatus, name="assessment_status_enum", native_enum=False),
        nullable=False,
        default=AssessmentStatus.DRAFT,
        index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    skill: Mapped["Skill"] = relationship(
        "Skill",
        lazy="joined",
    )
    role: Mapped["Role | None"] = relationship(
        "Role",
        lazy="joined",
    )
    questions: Mapped[list["AssessmentQuestion"]] = relationship(
        "AssessmentQuestion",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentQuestion.display_order.asc()",
        lazy="selectin",
    )
    attempts: Mapped[list["AssessmentAttempt"]] = relationship(
        "AssessmentAttempt",
        back_populates="assessment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
