"""add disclaimer column to recipes

Revision ID: 0002_add_disclaimer
Revises: 0003_skipped_urls_reason
Create Date: 2026-08-06
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_disclaimer"
down_revision = "0003_skipped_urls_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("disclaimer", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("recipes", "disclaimer")
