"""add reason column to skipped_urls

Revision ID: 0003_skipped_urls_reason
Revises: 0002_add_skipped_urls
Create Date: 2026-08-02
"""

from alembic import op

revision = "0003_skipped_urls_reason"
down_revision = "0002_add_skipped_urls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE skipped_urls ADD COLUMN IF NOT EXISTS reason TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE skipped_urls DROP COLUMN IF EXISTS reason")
