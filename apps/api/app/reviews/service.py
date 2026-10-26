"""Revisões por tópico (R07): criadas por sessões de teoria, dispensadas quando a origem some."""

import uuid
from collections import Counter
from collections.abc import Iterable
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.reviews import card_sort_key, is_duplicate, place_due, suggest_due_dates
from app.errors import ApiError
from app.flashcards.service import card_out
from app.models import Flashcard, ReviewTask, StudySession
from app.planning.service import current_plan


def create_for_session(db: Session, session: StudySession, topic_ids: Iterable[str] | None = None,
                       not_before: date | None = None) -> None:
    if session.activity != "theory" or session.deleted_at is not None:
        return
    exam_on = current_plan(db).exam_version.exam_date
    load = Counter(db.scalars(select(ReviewTask.due_on).where(ReviewTask.status == "pending")))
    for topic_id in sorted(set(session.topic_ids if topic_ids is None else topic_ids)):
        pending = list(db.scalars(select(ReviewTask.due_on).where(
            ReviewTask.topic_id == topic_id, ReviewTask.status == "pending")))
        existing = set(db.scalars(select(ReviewTask.offset_days).where(
            ReviewTask.session_id == session.id, ReviewTask.topic_id == topic_id)))
        for offset, due_on in suggest_due_dates(session.studied_on, exam_on):
            if offset in existing or (not_before and due_on < not_before) or is_duplicate(due_on, pending):
                continue
            placed = place_due(due_on, load, exam_on)
            if placed is None:
                continue
            db.add(ReviewTask(session_id=session.id, topic_id=topic_id, offset_days=offset, due_on=placed))
            pending.append(placed)
            load[placed] += 1
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


def approved_cards(db: Session, topic_id: str) -> list[Flashcard]:
    return list(db.scalars(select(Flashcard).where(Flashcard.topic_id == topic_id, Flashcard.status == "approved")))


def review_out(r: ReviewTask, today: date, cards_count: int) -> dict:
    return {"id": str(r.id), "version": r.version, "session_id": str(r.session_id), "topic_id": r.topic_id,
            "offset_days": r.offset_days, "due_on": r.due_on, "status": r.status, "completed_on": r.completed_on,
            "late": r.status == "pending" and r.due_on < today, "cards_count": cards_count}


def card_counts(db: Session) -> dict[str, int]:
    return dict(db.execute(select(Flashcard.topic_id, func.count()).where(Flashcard.status == "approved")
                           .group_by(Flashcard.topic_id)).all())


def list_reviews(db: Session, start: date, end: date, today: date) -> list[dict]:
    rows = db.scalars(select(ReviewTask).where(or_(
        (ReviewTask.status == "pending") & (ReviewTask.due_on <= end),
        (ReviewTask.status == "completed") & ReviewTask.completed_on.between(start, end),
        (ReviewTask.status == "dismissed") & ReviewTask.due_on.between(start, end),
    )).order_by(ReviewTask.due_on, ReviewTask.topic_id))
    counts = card_counts(db)
    return [review_out(r, today, counts.get(r.topic_id, 0)) for r in rows]


def _review(db: Session, review_id: uuid.UUID) -> ReviewTask:
    review = db.get(ReviewTask, review_id)
    if review is None:
        raise ApiError(404, "not_found", "Revisão não encontrada.")
    return review


def review_detail(db: Session, review_id: uuid.UUID, today: date) -> dict:
    review = _review(db, review_id)
    cards = sorted(approved_cards(db, review.topic_id), key=lambda c: card_sort_key(c.last_rating, c.created_at))
    return {**review_out(review, today, len(cards)), "cards": [card_out(c) for c in cards]}


def complete(db: Session, review_id: uuid.UUID, today: date) -> ReviewTask:
    review = _review(db, review_id)
    if review.status != "pending":
        raise ApiError(422, "not_pending", "Esta revisão já foi concluída ou dispensada.")
    review.status, review.completed_on = "completed", today
    review.version += 1
    overdue = db.scalars(select(ReviewTask).where(
        ReviewTask.topic_id == review.topic_id, ReviewTask.status == "pending", ReviewTask.due_on < today,
        ReviewTask.id != review.id))
    for other in overdue:  # atrasadas do tópico fecham junto, sem XP próprio (closed_by)
        other.status, other.completed_on, other.closed_by = "completed", today, review.id
        other.version += 1
    db.flush()
    return review


def dismiss(db: Session, review_id: uuid.UUID) -> ReviewTask:
    review = _review(db, review_id)
    if review.status != "pending":
        raise ApiError(422, "not_pending", "Esta revisão já foi concluída ou dispensada.")
    review.status = "dismissed"
    review.version += 1
    db.flush()
    return review
