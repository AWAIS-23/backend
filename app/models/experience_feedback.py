import uuid
from typing import TYPE_CHECKING
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.experience import Experience
    from app.models.organization import Organization
    from app.models.profile import Profile


class ExperienceFeedback(Base, TimestampMixin):
    """
    Structured performance feedback from an employer reviewer evaluating
    a candidate's practical performance during a real work experience.
    """
    __tablename__ = "experience_feedbacks"
    __table_args__ = (
        UniqueConstraint(
            "experience_id",
            "reviewer_id",
            name="uq_experience_reviewer_feedback",
        ),
        CheckConstraint(
            "overall_rating >= 1 AND overall_rating <= 5",
            name="chk_feedback_overall_rating_range",
        ),
        CheckConstraint(
            "communication_rating IS NULL OR (communication_rating >= 1 AND communication_rating <= 5)",
            name="chk_feedback_communication_rating_range",
        ),
        CheckConstraint(
            "technical_rating IS NULL OR (technical_rating >= 1 AND technical_rating <= 5)",
            name="chk_feedback_technical_rating_range",
        ),
        CheckConstraint(
            "problem_solving_rating IS NULL OR (problem_solving_rating >= 1 AND problem_solving_rating <= 5)",
            name="chk_feedback_problem_solving_rating_range",
        ),
        CheckConstraint(
            "teamwork_rating IS NULL OR (teamwork_rating >= 1 AND teamwork_rating <= 5)",
            name="chk_feedback_teamwork_rating_range",
        ),
        CheckConstraint(
            "professionalism_rating IS NULL OR (professionalism_rating >= 1 AND professionalism_rating <= 5)",
            name="chk_feedback_professionalism_rating_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    experience_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("experiences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The learner/candidate receiving this feedback",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="The employer reviewer who submitted this feedback",
    )
    overall_rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    strengths: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    areas_for_improvement: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    communication_rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    technical_rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    problem_solving_rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    teamwork_rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    professionalism_rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    recommendation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    experience: Mapped["Experience"] = relationship(
        "Experience",
        back_populates="feedbacks",
        lazy="joined",
    )
    profile: Mapped["Profile"] = relationship(
        "Profile",
        foreign_keys=[profile_id],
        lazy="joined",
    )
    organization: Mapped["Organization"] = relationship(
        "Organization",
        lazy="joined",
    )
    reviewer: Mapped["Profile"] = relationship(
        "Profile",
        foreign_keys=[reviewer_id],
        lazy="joined",
    )
