import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.role import RoleSkill


class Skill(Base):
    """
    Standardized skill entity supporting hierarchical taxonomy.
    Examples:
      - Backend Development (parent) -> Python -> FastAPI
      - Frontend Development (parent) -> React -> Next.js
    """
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    parent_skill_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("skills.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Hierarchical Self-Referential Relationships
    parent: Mapped["Skill | None"] = relationship(
        "Skill",
        remote_side=[id],
        back_populates="children",
        lazy="selectin",
    )
    children: Mapped[list["Skill"]] = relationship(
        "Skill",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    role_skills: Mapped[list["RoleSkill"]] = relationship(
        "RoleSkill",
        back_populates="skill",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
