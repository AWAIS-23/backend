"""Add educations table

Revision ID: 007_add_educations
Revises: 006_add_results_updated_at
Create Date: 2026-09-01 11:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "007_add_educations"
down_revision: Union[str, None] = "006_add_results_updated_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "educations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "profile_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("degree", sa.String(255), nullable=False),
        sa.Column("institution", sa.String(255), nullable=False),
        sa.Column("field_of_study", sa.String(255), nullable=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("grade", sa.String(50), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("educations")
