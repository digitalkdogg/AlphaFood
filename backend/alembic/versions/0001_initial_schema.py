"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-01
"""

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE scrapertype AS ENUM (
                'wordpress', 'generic_rss', 'html_sitemap', 'single_page'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE scrapestatus AS ENUM (
                'running', 'success', 'partial', 'error'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT NOT NULL UNIQUE,
            hashed_password TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            scraper_type scrapertype NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            frequency_hours INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_scraped_at TIMESTAMPTZ
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            source_url TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            ingredients JSONB,
            instructions JSONB,
            prep_time INTEGER,
            cook_time INTEGER,
            servings TEXT,
            image_url TEXT,
            is_dairy_free BOOLEAN,
            mentions_mammal_ingredients BOOLEAN NOT NULL DEFAULT FALSE,
            needs_review BOOLEAN NOT NULL DEFAULT TRUE,
            published BOOLEAN NOT NULL DEFAULT FALSE,
            extracted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS scrape_runs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_id UUID REFERENCES sources(id) ON DELETE CASCADE,
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at TIMESTAMPTZ,
            status scrapestatus NOT NULL DEFAULT 'running',
            recipes_found INTEGER NOT NULL DEFAULT 0,
            recipes_added INTEGER NOT NULL DEFAULT 0,
            recipes_updated INTEGER NOT NULL DEFAULT 0,
            recipes_skipped_non_recipe INTEGER NOT NULL DEFAULT 0,
            error_message TEXT
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS scrape_runs")
    op.execute("DROP TABLE IF EXISTS recipes")
    op.execute("DROP TABLE IF EXISTS sources")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TYPE IF EXISTS scrapestatus")
    op.execute("DROP TYPE IF EXISTS scrapertype")
