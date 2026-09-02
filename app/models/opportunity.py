import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.constants import OpportunityStatus, OpportunityType
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.match import Match
    from app.models.opportunity_skill import OpportunitySkill
    from app.models.organization import Organization
    from app.models.profile import Profile


class Opportunity(Base, TimestampMixin):
    """
    Career opportunity published by an employer organization
    (Job, Internship, Apprenticeship, or Project).
    """
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
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
    opportunity_type: Mapped[OpportunityType] = mapped_column(
        SQLEnum(OpportunityType, name="opportunity_type_enum", native_enum=False),
        nullable=False,
        default=OpportunityType.JOB,
        index=True,
    )
    status: Mapped[OpportunityStatus] = mapped_column(
        SQLEnum(OpportunityStatus, name="opportunity_status_enum", native_enum=False),
        nullable=False,
        default=OpportunityStatus.DRAFT,
        index=True,
    )
    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    is_remote: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        lazy="joined",
    )
    creator: Mapped["Profile | None"] = relationship(
        "Profile",
        foreign_keys=[created_by],
        lazy="joined",
    )
    opportunity_skills: Mapped[list["OpportunitySkill"]] = relationship(
        "OpportunitySkill",
        back_populates="opportunity",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="opportunity",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    matches: Mapped[list["Match"]] = relationship(
        "Match",
        back_populates="opportunity",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
