"""Phase 4: Opportunities, Deterministic Matching & Applications

Revision ID: 004_phase4
Revises: 003_phase3
Create Date: 2026-08-30 22:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004_phase4"
down_revision: Union[str, None] = "003_phase3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Opportunities Table
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("opportunity_type", sa.String(length=50), nullable=False, server_default="job"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("is_remote", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunities_organization_id", "opportunities", ["organization_id"])
    op.create_index("ix_opportunities_title", "opportunities", ["title"])
    op.create_index("ix_opportunities_opportunity_type", "opportunities", ["opportunity_type"])
    op.create_index("ix_opportunities_status", "opportunities", ["status"])

    # 2. Opportunity Skills Table
    op.create_table(
        "opportunity_skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.Column("importance_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.CheckConstraint(
            "importance_weight >= 0.0 AND importance_weight <= 1.0",
            name="chk_opportunity_skill_weight_range",
        ),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opportunity_id", "skill_id", name="uq_opportunity_skill"),
    )
    op.create_index("ix_opportunity_skills_opportunity_id", "opportunity_skills", ["opportunity_id"])
    op.create_index("ix_opportunity_skills_skill_id", "opportunity_skills", ["skill_id"])

    # 3. Applications Table
    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="submitted"),
        sa.Column("cover_note", sa.Text(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opportunity_id", "profile_id", name="uq_opportunity_profile_application"),
    )
    op.create_index("ix_applications_opportunity_id", "applications", ["opportunity_id"])
    op.create_index("ix_applications_profile_id", "applications", ["profile_id"])
    op.create_index("ix_applications_status", "applications", ["status"])

    # 4. Matches Table
    op.create_table(
        "matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("skill_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("evidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("experience_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("breakdown", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "overall_score >= 0.0 AND overall_score <= 100.0",
            name="chk_match_overall_score_range",
        ),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opportunity_id", "profile_id", name="uq_opportunity_profile_match"),
    )
    op.create_index("ix_matches_opportunity_id", "matches", ["opportunity_id"])
    op.create_index("ix_matches_profile_id", "matches", ["profile_id"])


def downgrade() -> None:
    op.drop_table("matches")
    op.drop_table("applications")
    op.drop_table("opportunity_skills")
    op.drop_table("opportunities")
