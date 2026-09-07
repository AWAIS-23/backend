"""Add organization profile fields

Revision ID: 008_org_profile_fields
Revises: 007_add_educations
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "008_org_profile_fields"
down_revision: Union[str, None] = "007_add_educations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("location", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "description")
    op.drop_column("organizations", "location")