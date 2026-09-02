"""Phase 5: Experience, Feedback & In-App Notifications

Revision ID: 005_phase5
Revises: 004_phase4
Create Date: 2026-08-30 22:40:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005_phase5"
down_revision: Union[str, None] = "004_phase4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Experiences Table
    op.create_table(
        "experiences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("application_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("experience_type", sa.String(length=50), nullable=False, server_default="internship"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("verification_status", sa.String(length=50), nullable=False, server_default="unverified"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiences_profile_id", "experiences", ["profile_id"])
    op.create_index("ix_experiences_organization_id", "experiences", ["organization_id"])
    op.create_index("ix_experiences_opportunity_id", "experiences", ["opportunity_id"])
    op.create_index("ix_experiences_application_id", "experiences", ["application_id"])
    op.create_index("ix_experiences_title", "experiences", ["title"])
    op.create_index("ix_experiences_experience_type", "experiences", ["experience_type"])
    op.create_index("ix_experiences_status", "experiences", ["status"])
    op.create_index("ix_experiences_verification_status", "experiences", ["verification_status"])

    # 2. Experience Feedbacks Table
    op.create_table(
        "experience_feedbacks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("experience_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("overall_rating", sa.Integer(), nullable=False),
        sa.Column("strengths", sa.Text(), nullable=True),
        sa.Column("areas_for_improvement", sa.Text(), nullable=True),
        sa.Column("communication_rating", sa.Integer(), nullable=True),
        sa.Column("technical_rating", sa.Integer(), nullable=True),
        sa.Column("problem_solving_rating", sa.Integer(), nullable=True),
        sa.Column("teamwork_rating", sa.Integer(), nullable=True),
        sa.Column("professionalism_rating", sa.Integer(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "overall_rating >= 1 AND overall_rating <= 5",
            name="chk_feedback_overall_rating_range",
        ),
        sa.CheckConstraint(
            "communication_rating IS NULL OR (communication_rating >= 1 AND communication_rating <= 5)",
            name="chk_feedback_communication_rating_range",
        ),
        sa.CheckConstraint(
            "technical_rating IS NULL OR (technical_rating >= 1 AND technical_rating <= 5)",
            name="chk_feedback_technical_rating_range",
        ),
        sa.CheckConstraint(
            "problem_solving_rating IS NULL OR (problem_solving_rating >= 1 AND problem_solving_rating <= 5)",
            name="chk_feedback_problem_solving_rating_range",
        ),
        sa.CheckConstraint(
            "teamwork_rating IS NULL OR (teamwork_rating >= 1 AND teamwork_rating <= 5)",
            name="chk_feedback_teamwork_rating_range",
        ),
        sa.CheckConstraint(
            "professionalism_rating IS NULL OR (professionalism_rating >= 1 AND professionalism_rating <= 5)",
            name="chk_feedback_professionalism_rating_range",
        ),
        sa.ForeignKeyConstraint(["experience_id"], ["experiences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["profiles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experience_id", "reviewer_id", name="uq_experience_reviewer_feedback"),
    )
    op.create_index("ix_experience_feedbacks_experience_id", "experience_feedbacks", ["experience_id"])
    op.create_index("ix_experience_feedbacks_profile_id", "experience_feedbacks", ["profile_id"])
    op.create_index("ix_experience_feedbacks_organization_id", "experience_feedbacks", ["organization_id"])
    op.create_index("ix_experience_feedbacks_reviewer_id", "experience_feedbacks", ["reviewer_id"])

    # 3. Notifications Table
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False, server_default="application_status"),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_profile_id", "notifications", ["profile_id"])
    op.create_index("ix_notifications_notification_type", "notifications", ["notification_type"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("experience_feedbacks")
    op.drop_table("experiences")
