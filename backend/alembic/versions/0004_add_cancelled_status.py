"""add cancelled value to scrapestatus enum

Revision ID: 0004_add_cancelled_status
Revises: 0002_add_disclaimer
Create Date: 2026-08-06
"""

from alembic import op

revision = "0004_add_cancelled_status"
down_revision = "0002_add_disclaimer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE scrapestatus ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values; downgrade is a no-op
    pass
