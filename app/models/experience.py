import uuid
from datetime import datetime, timezone
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
from app.core.constants import ExperienceStatus, ExperienceType, VerificationStatus
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.experience_feedback import ExperienceFeedback
    from app.models.opportunity import Opportunity
    from app.models.organization import Organization
    from app.models.profile import Profile


class Experience(Base, TimestampMixin):
    """
    Practical work engagement or professional experience performed by a candidate.
    """
    __tablename__ = "experiences"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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
    experience_type: Mapped[ExperienceType] = mapped_column(
        SQLEnum(ExperienceType, name="experience_type_enum", native_enum=False),
        nullable=False,
        default=ExperienceType.INTERNSHIP,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[ExperienceStatus] = mapped_column(
        SQLEnum(ExperienceStatus, name="experience_status_enum", native_enum=False),
        nullable=False,
        default=ExperienceStatus.ACTIVE,
        index=True,
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SQLEnum(VerificationStatus, name="experience_verification_status_enum", native_enum=False),
        nullable=False,
        default=VerificationStatus.UNVERIFIED,
        index=True,
    )

    # Relationships
    profile: Mapped["Profile"] = relationship(
        "Profile",
        foreign_keys=[profile_id],
        lazy="joined",
    )
    organization: Mapped["Organization | None"] = relationship(
        "Organization",
        lazy="joined",
    )
    opportunity: Mapped["Opportunity | None"] = relationship(
        "Opportunity",
        lazy="joined",
    )
    application: Mapped["Application | None"] = relationship(
        "Application",
        lazy="joined",
    )
    feedbacks: Mapped[list["ExperienceFeedback"]] = relationship(
        "ExperienceFeedback",
        back_populates="experience",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
