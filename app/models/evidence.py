import uuid
from typing import Any, TYPE_CHECKING
from sqlalchemy import (
    CheckConstraint,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    JSON,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.constants import EvidenceSourceType, EvidenceStatus
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.profile import Profile
    from app.models.skill import Skill
    from app.models.verification import Verification


class Evidence(Base, TimestampMixin):
    """
    Skill evidence record capturing a learner's demonstrated capability.

    CRITICAL DESIGN RULES:
    1. Evidence is ALWAYS created by the backend service, never directly by the learner.
    2. Once status == 'verified', score and provenance fields are IMMUTABLE.
    3. AI may NOT set status = 'verified'. Only authorized human verifiers can do that.
    4. source_type + source_id preserve full provenance (which assessment or submission generated this).
    """
    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint(
            "score >= 0.0 AND score <= 100.0",
            name="chk_evidence_score_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[EvidenceSourceType] = mapped_column(
        SQLEnum(EvidenceSourceType, name="evidence_source_type_enum", native_enum=False),
        nullable=False,
        index=True,
        doc="The type of activity that generated this evidence.",
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
        doc="FK to the specific source record (evaluation.id or assessment_result.id).",
    )
    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Score from the originating evaluation or assessment (0-100).",
    )
    evidence_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Snapshot of provenance data at time of evidence creation.",
    )
    status: Mapped[EvidenceStatus] = mapped_column(
        SQLEnum(EvidenceStatus, name="evidence_status_enum", native_enum=False),
        nullable=False,
        default=EvidenceStatus.UNVERIFIED,
        index=True,
    )

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", lazy="joined")
    skill: Mapped["Skill"] = relationship("Skill", lazy="joined")
    verifications: Mapped[list["Verification"]] = relationship(
        "Verification",
        back_populates="evidence",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
