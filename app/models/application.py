import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.constants import ApplicationStatus
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.profile import Profile


class Application(Base, TimestampMixin):
    """
    Learner application to a specific career opportunity.
    Unique per (opportunity_id, profile_id).
    """
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id",
            "profile_id",
            name="uq_opportunity_profile_application",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, name="application_status_enum", native_enum=False),
        nullable=False,
        default=ApplicationStatus.SUBMITTED,
        index=True,
    )
    cover_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    opportunity: Mapped["Opportunity"] = relationship(
        "Opportunity",
        back_populates="applications",
        lazy="joined",
    )
    profile: Mapped["Profile"] = relationship(
        "Profile",
        foreign_keys=[profile_id],
        lazy="joined",
    )
    reviewer: Mapped["Profile | None"] = relationship(
        "Profile",
        foreign_keys=[reviewed_by],
        lazy="joined",
    )
