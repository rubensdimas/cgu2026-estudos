"""reviews

Revision ID: 6b1e4d8a2c57
Revises: 3f7a9c1d2e84
Create Date: 2026-10-21 20:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.clock import get_today
from app.reviews.service import create_from_history

revision = "6b1e4d8a2c57"
down_revision = "3f7a9c1d2e84"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("flashcards", sa.Column("last_rating", sa.String(length=16), nullable=True))
    op.add_column("flashcards", sa.Column("rated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "ck_flashcard_rating", "flashcards",
        "last_rating is null or last_rating in ('nao_lembrei','palpite','parcial','lembrei')")
    op.create_table(
        "review_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("study_sessions.id"), nullable=False),
        sa.Column("topic_id", sa.String(length=16), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column("offset_days", sa.Integer(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("completed_on", sa.Date(), nullable=True),
        sa.Column("closed_by", sa.Uuid(), sa.ForeignKey("review_tasks.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("session_id", "topic_id", "offset_days", name="uq_review_session_topic_offset"),
        sa.CheckConstraint("status in ('pending','completed','dismissed')", name="ck_review_status"),
        sa.CheckConstraint("offset_days > 0", name="ck_review_offset"),
    )
    op.create_index("ix_review_tasks_session_id", "review_tasks", ["session_id"])
    op.create_index("ix_review_tasks_topic_id", "review_tasks", ["topic_id"])
    op.create_index("ix_review_tasks_due_on", "review_tasks", ["due_on"])
    # Histórico: só revisões de hoje em diante, para não nascer uma fila de atrasadas (decisão de 21/10).
    db = Session(bind=op.get_bind())
    create_from_history(db, get_today())
    db.flush()


def downgrade() -> None:
    op.drop_table("review_tasks")
    op.drop_constraint("ck_flashcard_rating", "flashcards", type_="check")
    op.drop_column("flashcards", "rated_at")
    op.drop_column("flashcards", "last_rating")
