"""add meal_category to recipes

Revision ID: 0006_add_meal_category
Revises: 0005_add_permanent_skip
Create Date: 2026-08-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_add_meal_category"
down_revision = "0005_add_permanent_skip"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("meal_category", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("recipes", "meal_category")
