import uuid
from typing import TYPE_CHECKING
from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.challenge import Challenge
    from app.models.skill import Skill


class ChallengeSkill(Base):
    """
    Many-to-many relationship between Challenge and Skill with importance weighting.
    Mirrors the RoleSkill pattern established in Phase 1.
    """
    __tablename__ = "challenge_skills"
    __table_args__ = (
        UniqueConstraint("challenge_id", "skill_id", name="uq_challenge_skill"),
        CheckConstraint(
            "importance_weight >= 0.0 AND importance_weight <= 1.0",
            name="chk_challenge_skill_weight_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    importance_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        doc="Relative importance of this skill for the challenge (0.0–1.0).",
    )

    # Relationships
    challenge: Mapped["Challenge"] = relationship(
        "Challenge", back_populates="challenge_skills", lazy="joined"
    )
    skill: Mapped["Skill"] = relationship("Skill", lazy="joined")
