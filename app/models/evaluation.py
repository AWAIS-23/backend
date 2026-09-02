import uuid
from typing import Any, TYPE_CHECKING
from sqlalchemy import (
    CheckConstraint,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.profile import Profile
    from app.models.submission import Submission


class EvaluationStatus(str):
    """Inline status constants for evaluation lifecycle."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"


class Evaluation(Base, TimestampMixin):
    """
    Structured rubric-based assessment of a learner submission.

    SECURITY:
    - evaluator_id is ALWAYS set from the authenticated JWT, never from the request body.
    - score is ALWAYS computed server-side from the rubric; the client never supplies it.
    - A learner cannot evaluate their own submission (enforced in EvaluationService).

    Rubric format (stored as JSON):
    [
      {"criterion": "Technical Correctness", "max_points": 25, "awarded_points": 22},
      {"criterion": "Code Quality",          "max_points": 25, "awarded_points": 20},
      ...
    ]
    The server recalculates score = sum(awarded) / sum(max) * 100.
    """
    __tablename__ = "evaluations"
    __table_args__ = (
        CheckConstraint(
            "score >= 0.0 AND score <= 100.0",
            name="chk_evaluation_score_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("submissions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evaluator_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Always derived from JWT. Never from request body.",
    )
    rubric: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        doc="List of rubric items: [{criterion, max_points, awarded_points}]",
    )
    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Server-calculated score (0-100). Never trusted from client.",
    )
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="submitted",
        index=True,
    )

    # Relationships
    submission: Mapped["Submission"] = relationship(
        "Submission", back_populates="evaluations", lazy="joined"
    )
    evaluator: Mapped["Profile"] = relationship("Profile", lazy="joined")
    evidence: Mapped["Evidence | None"] = relationship(
        "Evidence",
        foreign_keys="Evidence.source_id",
        primaryjoin="and_(Evidence.source_id == Evaluation.id, "
                    "Evidence.source_type == 'challenge_submission')",
        lazy="joined",
        viewonly=True,
    )
