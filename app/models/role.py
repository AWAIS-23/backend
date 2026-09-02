import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.skill import Skill


class Role(Base):
    """
    Standardized career role entity (e.g. Frontend Developer, Backend Developer).
    """
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    role_skills: Mapped[list["RoleSkill"]] = relationship(
        "RoleSkill",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class RoleSkill(Base):
    """
    Junction entity mapping skills required for a role along with relative importance weight.
    Constraint: 0.0 <= importance_weight <= 1.0
    """
    __tablename__ = "role_skills"
    __table_args__ = (
        UniqueConstraint("role_id", "skill_id", name="uq_role_skill"),
        CheckConstraint(
            "importance_weight >= 0.0 AND importance_weight <= 1.0",
            name="chk_role_skill_weight",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    importance_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )

    # Relationships
    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="role_skills",
        lazy="joined",
    )
    skill: Mapped["Skill"] = relationship(
        "Skill",
        back_populates="role_skills",
        lazy="joined",
    )
