"""flashcards

Revision ID: 3f7a9c1d2e84
Revises: 8d4b2e6f1a90
Create Date: 2026-10-21 15:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "3f7a9c1d2e84"
down_revision = "8d4b2e6f1a90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "flashcard_batches",
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("study_sessions.id"), primary_key=True),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("studied", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("focus", sa.Text(), nullable=False),
        sa.Column("priorities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "flashcards",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("study_sessions.id"), nullable=False),
        sa.Column("topic_id", sa.String(length=16), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column("subitem", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("front", sa.Text(), nullable=False),
        sa.Column("back", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("status in ('draft','approved')", name="ck_flashcard_status"),
        sa.CheckConstraint(
            "category in ('conceito','distincao','condicao','causa_consequencia','aplicacao','erro_recorrente',"
            "'fundamentacao')", name="ck_flashcard_category"),
    )
    op.create_index("ix_flashcards_session_id", "flashcards", ["session_id"])
    op.create_index("ix_flashcards_topic_id", "flashcards", ["topic_id"])


def downgrade() -> None:
    op.drop_table("flashcards")
    op.drop_table("flashcard_batches")
