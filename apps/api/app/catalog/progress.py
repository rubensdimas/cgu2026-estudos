"""Promoção automática do estado declarado por tópico (R08) a partir de sessões de teoria.

Só sobe na ordem de RANK, nunca rebaixa; excluir sessão ou reabrir bloco não reverte nada.
"""

import uuid
from collections.abc import Iterable
from datetime import date
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Occurrence, StudySession, TopicProgress

RANK = ("not_started", "in_progress", "first_pass", "reviewed")


def promote(db: Session, topic_ids: Iterable[str], status: Literal["in_progress", "first_pass"], on: date) -> None:
    for topic_id in sorted(set(topic_ids)):
        row = db.get(TopicProgress, topic_id)
        if row is None:
            db.add(TopicProgress(topic_id=topic_id, status=status, declared_on=on))
        elif RANK.index(status) > RANK.index(row.status):
            row.status, row.declared_on = status, on
            row.version += 1
    db.flush()


def promote_for_session(db: Session, session: StudySession, topic_ids: Iterable[str] | None = None) -> None:
    if session.activity != "theory" or session.deleted_at is not None:
        return
    occurrence = db.get(Occurrence, session.occurrence_id) if session.occurrence_id else None
    status = "in_progress" if occurrence is not None and occurrence.status != "completed" else "first_pass"
    promote(db, session.topic_ids if topic_ids is None else topic_ids, status, session.studied_on)


def promote_for_occurrence(db: Session, occurrence: Occurrence) -> None:
    if occurrence.status == "completed":
        for session in _theory_sessions(db, occurrence.id):
            promote_for_session(db, session)


def promote_from_history(db: Session) -> None:
    for session in _theory_sessions(db):
        promote_for_session(db, session)


def _theory_sessions(db: Session, occurrence_id: uuid.UUID | None = None) -> list[StudySession]:
    query = select(StudySession).where(StudySession.deleted_at.is_(None), StudySession.activity == "theory")
    if occurrence_id is not None:
        query = query.where(StudySession.occurrence_id == occurrence_id)
    return list(db.scalars(query.order_by(StudySession.studied_on, StudySession.created_at)))
