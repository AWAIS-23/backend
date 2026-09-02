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
    from app.models.opportunity import Opportunity
    from app.models.skill import Skill


class OpportunitySkill(Base):
    """
    Many-to-many relationship mapping an Opportunity to its required Skills
    along with relative importance weights (0.0 to 1.0).
    """
    __tablename__ = "opportunity_skills"
    __table_args__ = (
        UniqueConstraint("opportunity_id", "skill_id", name="uq_opportunity_skill"),
        CheckConstraint(
            "importance_weight >= 0.0 AND importance_weight <= 1.0",
            name="chk_opportunity_skill_weight_range",
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
        doc="Relative weight of this skill requirement (0.0 to 1.0)",
    )

    # Relationships
    opportunity: Mapped["Opportunity"] = relationship(
        "Opportunity",
        back_populates="opportunity_skills",
        lazy="joined",
    )
    skill: Mapped["Skill"] = relationship(
        "Skill",
        lazy="joined",
    )
