"""occurrence theme

Revision ID: 5c9e1f3a7b21
Revises: 2a16732b4a43
Create Date: 2026-10-10 18:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "5c9e1f3a7b21"
down_revision = "2a16732b4a43"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("occurrences", sa.Column("theme_id", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("occurrences", "theme_id")
