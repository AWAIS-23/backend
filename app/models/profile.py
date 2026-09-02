import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Enum as SQLEnum, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.constants import UserRole
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import OrganizationMember


class Profile(Base, TimestampMixin):
    """
    Profile entity representing user domain identity.
    The primary key 'id' directly matches Supabase auth.users.id.
    """
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Directly corresponds to Supabase auth.users.id",
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role_enum", native_enum=False),
        nullable=False,
        default=UserRole.LEARNER,
        index=True,
    )
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    memberships: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
