"""Phase 1: Profiles, Organizations, Skills and Roles

Revision ID: 001_phase1
Revises: 
Create Date: 2026-08-30 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_phase1"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Profiles Table
    op.create_table(
        "profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=1024), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="learner"),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_profiles_full_name", "profiles", ["full_name"], unique=False)
    op.create_index("ix_profiles_role", "profiles", ["role"], unique=False)

    # 2. Organizations Table
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("website_url", sa.String(length=1024), nullable=True),
        sa.Column("logo_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_name", "organizations", ["name"], unique=False)

    # 3. Organization Members Junction Table
    op.create_table(
        "organization_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("org_role", sa.String(length=50), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "profile_id", name="uq_org_member"),
    )
    op.create_index("ix_org_members_org_id", "organization_members", ["organization_id"], unique=False)
    op.create_index("ix_org_members_profile_id", "organization_members", ["profile_id"], unique=False)
    op.create_index("ix_org_members_org_role", "organization_members", ["org_role"], unique=False)

    # 4. Skills Table
    op.create_table(
        "skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_skill_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_skill_id"], ["skills.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_skills_name"),
    )
    op.create_index("ix_skills_name", "skills", ["name"], unique=True)
    op.create_index("ix_skills_category", "skills", ["category"], unique=False)
    op.create_index("ix_skills_parent_skill_id", "skills", ["parent_skill_id"], unique=False)

    # 5. Roles Table
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("title", name="uq_roles_title"),
    )
    op.create_index("ix_roles_title", "roles", ["title"], unique=True)

    # 6. Role Skills Junction Table
    op.create_table(
        "role_skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.Column("importance_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.CheckConstraint(
            "importance_weight >= 0.0 AND importance_weight <= 1.0",
            name="chk_role_skill_weight",
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "skill_id", name="uq_role_skill"),
    )
    op.create_index("ix_role_skills_role_id", "role_skills", ["role_id"], unique=False)
    op.create_index("ix_role_skills_skill_id", "role_skills", ["skill_id"], unique=False)


def downgrade() -> None:
    op.drop_table("role_skills")
    op.drop_table("roles")
    op.drop_table("skills")
    op.drop_table("organization_members")
    op.drop_table("organizations")
    op.drop_table("profiles")
