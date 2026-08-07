"""add permanent flag to skipped_urls

Revision ID: 0005_add_permanent_skip
Revises: 0004_add_cancelled_status
Create Date: 2026-08-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_add_permanent_skip"
down_revision = "0004_add_cancelled_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "skipped_urls",
        sa.Column("permanent", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("skipped_urls", "permanent")
