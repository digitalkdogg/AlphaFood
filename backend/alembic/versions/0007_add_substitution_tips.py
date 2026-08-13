"""add substitution_tips to recipes

Revision ID: 0007_add_substitution_tips
Revises: 0006_add_meal_category
Create Date: 2026-08-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_add_substitution_tips"
down_revision = "0006_add_meal_category"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("recipes", sa.Column("substitution_tips", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("recipes", "substitution_tips")
