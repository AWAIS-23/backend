import uuid
from typing import TYPE_CHECKING
from sqlalchemy import (
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.profile import Profile


class Verification(Base, TimestampMixin):
    """
    Immutable audit log entry recording an evidence state transition.

    A new Verification row is created every time an authorized human
    approves or rejects evidence — it is never mutated.

    SECURITY:
    - verifier_id is always set from the JWT, never from the request body.
    - AI cannot create Verification records that set status = 'verified'.
    - from_status + to_status provide a full audit trail.
    - Self-verification (verifier == evidence.profile_id) is blocked in VerificationService.
    """
    __tablename__ = "verifications"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    verifier_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Identity of the authorized verifier, derived from JWT.",
    )
    from_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Evidence status before this transition.",
    )
    to_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Evidence status after this transition.",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Optional verifier notes explaining the decision.",
    )

    # Relationships
    evidence: Mapped["Evidence"] = relationship(
        "Evidence", back_populates="verifications", lazy="joined"
    )
    verifier: Mapped["Profile"] = relationship("Profile", lazy="joined")
