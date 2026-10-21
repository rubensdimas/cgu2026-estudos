"""topic progress backfill

Revision ID: 8d4b2e6f1a90
Revises: 5c9e1f3a7b21
Create Date: 2026-10-21 12:00:00
"""
from alembic import op
from sqlalchemy.orm import Session

from app.catalog.progress import promote_from_history

revision = "8d4b2e6f1a90"
down_revision = "5c9e1f3a7b21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Usa o ORM atual de propósito: app de usuário único, a migração roda uma vez e reaproveita a regra testada.
    db = Session(bind=op.get_bind())
    promote_from_history(db)
    db.flush()


def downgrade() -> None:
    # Estado declarado não é revertido (R08): o ajuste é manual no Edital.
    pass
