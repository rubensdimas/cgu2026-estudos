"""Revisões por tópico (R07): criadas por sessões de teoria, dispensadas quando a origem some."""

import uuid
from collections.abc import Iterable
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.reviews import is_duplicate, suggest_due_dates
from app.models import ReviewTask, StudySession
from app.planning.service import current_plan


def create_for_session(db: Session, session: StudySession, topic_ids: Iterable[str] | None = None,
                       not_before: date | None = None) -> None:
    if session.activity != "theory" or session.deleted_at is not None:
        return
    exam_on = current_plan(db).exam_version.exam_date
    for topic_id in sorted(set(session.topic_ids if topic_ids is None else topic_ids)):
        pending = list(db.scalars(select(ReviewTask.due_on).where(
            ReviewTask.topic_id == topic_id, ReviewTask.status == "pending")))
        existing = set(db.scalars(select(ReviewTask.offset_days).where(
            ReviewTask.session_id == session.id, ReviewTask.topic_id == topic_id)))
        for offset, due_on in suggest_due_dates(session.studied_on, exam_on):
            if offset in existing or (not_before and due_on < not_before) or is_duplicate(due_on, pending):
                continue
            db.add(ReviewTask(session_id=session.id, topic_id=topic_id, offset_days=offset, due_on=due_on))
            pending.append(due_on)
    db.flush()


def dismiss_for_session(db: Session, session_id: uuid.UUID, topic_ids: Iterable[str] | None = None) -> None:
    query = select(ReviewTask).where(ReviewTask.session_id == session_id, ReviewTask.status == "pending")
    if topic_ids is not None:
        query = query.where(ReviewTask.topic_id.in_(list(topic_ids)))
    for review in db.scalars(query):
        review.status = "dismissed"
        review.version += 1
    db.flush()


def create_from_history(db: Session, today: date) -> None:
    sessions = db.scalars(select(StudySession).where(
        StudySession.deleted_at.is_(None), StudySession.activity == "theory",
    ).order_by(StudySession.studied_on, StudySession.created_at))
    for session in list(sessions):
        create_for_session(db, session, not_before=today)
