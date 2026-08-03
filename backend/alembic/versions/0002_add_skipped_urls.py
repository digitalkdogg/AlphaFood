"""add skipped_urls table

Revision ID: 0002_add_skipped_urls
Revises: 0001_initial
Create Date: 2026-08-02
"""

from alembic import op

revision = "0002_add_skipped_urls"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS skipped_urls (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            url TEXT NOT NULL UNIQUE,
            skipped_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_skipped_urls_url ON skipped_urls (url)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS skipped_urls")
