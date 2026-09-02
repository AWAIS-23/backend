import uuid
from typing import Any, TYPE_CHECKING
from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    JSON,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.profile import Profile


class Match(Base, TimestampMixin):
    """
    Deterministic skill match score and transparent breakdown connecting
    a candidate's verified evidence to an opportunity's required skills.
    """
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id",
            "profile_id",
            name="uq_opportunity_profile_match",
        ),
        CheckConstraint(
            "overall_score >= 0.0 AND overall_score <= 100.0",
            name="chk_match_overall_score_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Weighted composite score: 0.60*skill + 0.30*evidence + 0.10*experience",
    )
    skill_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    evidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    experience_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Explainable breakdown of matched skills, verified coverage, and weights",
    )

    # Relationships
    opportunity: Mapped["Opportunity"] = relationship(
        "Opportunity",
        back_populates="matches",
        lazy="joined",
    )
    profile: Mapped["Profile"] = relationship(
        "Profile",
        lazy="joined",
    )
