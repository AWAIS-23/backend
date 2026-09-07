import uuid
from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import (
    Date,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.profile import Profile


class Education(Base, TimestampMixin):
    """
    Academic background record for a learner profile.
    """
    __tablename__ = "educations"

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
    degree: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    institution: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    field_of_study: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    grade: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    profile: Mapped["Profile"] = relationship(
        "Profile",
        foreign_keys=[profile_id],
        lazy="joined",
    )
