"""Flashcards de sessões de teoria (R13): geração como rascunho, aprovação e baralho por tópico."""

import uuid
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.flashcards.ai import AiError, Generator
from app.flashcards.domain import Context
from app.guidance import content
from app.models import Flashcard, FlashcardBatch, StudySession, Subject, Topic

_ORDER = (Flashcard.created_at, Flashcard.id)


def card_out(c: Flashcard) -> dict:
    return {"id": str(c.id), "version": c.version, "session_id": str(c.session_id), "topic_id": c.topic_id,
            "subitem": c.subitem, "category": c.category, "front": c.front, "back": c.back, "status": c.status}


def _batch_out(b: FlashcardBatch | None) -> dict | None:
    if b is None:
        return None
    return {"model": b.model, "studied": b.studied, "origin": b.origin, "focus": b.focus,
            "priorities": b.priorities, "created_at": b.created_at}


def _theory_session(db: Session, session_id: uuid.UUID) -> StudySession:
    session = db.get(StudySession, session_id)
    if session is None or session.deleted_at is not None:
        raise ApiError(404, "not_found", "Sessão não encontrada.")
    if session.activity != "theory" or not session.topic_ids:
        raise ApiError(422, "not_theory", "Flashcards só para sessões de teoria com tópico.")
    return session


def session_flashcards(db: Session, session_id: uuid.UUID) -> dict:
    cards = db.scalars(select(Flashcard).where(Flashcard.session_id == session_id).order_by(*_ORDER))
    return {"batch": _batch_out(db.get(FlashcardBatch, session_id)), "cards": [card_out(c) for c in cards]}


def _context(db: Session, topic_id: str, studied: str) -> Context:
    topic = db.get(Topic, topic_id)
    data = content.guidance()
    return Context(subject=db.get(Subject, topic.subject_id).title, topic_id=topic.id, topic=topic.title,
                   subitems=data["subitens"].get(topic.id, []), materials=data["materiais"].get(topic.id, []),
                   studied=studied)


def generate(db: Session, session_id: uuid.UUID, studied: str, generator: Generator | None) -> dict:
    session = _theory_session(db, session_id)
    if generator is None:
        raise ApiError(503, "ai_disabled", "Configure OPENAI_API_KEY para gerar flashcards.")
    topic_id = session.topic_ids[0]
    try:
        batch = generator(_context(db, topic_id, studied))  # antes de qualquer escrita: falha não grava nada
    except AiError:
        raise ApiError(502, "ai_failed", "Não foi possível gerar agora. Tente novamente.") from None
    db.execute(delete(Flashcard).where(Flashcard.session_id == session_id, Flashcard.status == "draft"))
    db.execute(delete(FlashcardBatch).where(FlashcardBatch.session_id == session_id))
    db.add(FlashcardBatch(session_id=session_id, model=generator.model, studied=studied, origin=batch.origin,
                          focus=batch.focus, priorities=batch.priorities))
    for card in batch.cards:
        db.add(Flashcard(session_id=session_id, topic_id=topic_id, subitem=card.subitem, category=card.category,
                         front=card.front, back=card.back, status="draft"))
    db.flush()
    return session_flashcards(db, session_id)


def approve_all(db: Session, session_id: uuid.UUID) -> dict:
    for card in db.scalars(select(Flashcard).where(Flashcard.session_id == session_id, Flashcard.status == "draft")):
        card.status = "approved"
        card.version += 1
    db.flush()
    return session_flashcards(db, session_id)


def _card(db: Session, card_id: uuid.UUID) -> Flashcard:
    card = db.get(Flashcard, card_id)
    if card is None:
        raise ApiError(404, "not_found", "Cartão não encontrado.")
    return card


def patch_card(db: Session, card_id: uuid.UUID, version: int, changes: dict) -> Flashcard:
    card = _card(db, card_id)
    if version != card.version:
        raise ApiError(409, "version_conflict", "Este registro foi alterado. Recarregue antes de editar.")
    for field in ("front", "back", "status"):
        if changes.get(field) is not None:
            setattr(card, field, changes[field])
    card.version += 1
    db.flush()
    return card


def delete_card(db: Session, card_id: uuid.UUID) -> None:
    db.delete(_card(db, card_id))
    db.flush()


def deck(db: Session, topic_id: str | None) -> list[Flashcard]:
    query = select(Flashcard).where(Flashcard.status == "approved")
    if topic_id:
        query = query.where(Flashcard.topic_id == topic_id)
    return list(db.scalars(query.order_by(Flashcard.topic_id, *_ORDER)))


def theory_sessions(db: Session, start: date, end: date) -> list[dict]:
    sessions = [s for s in db.scalars(
        select(StudySession)
        .where(StudySession.deleted_at.is_(None), StudySession.activity == "theory",
               StudySession.studied_on.between(start, end))
        .order_by(StudySession.studied_on.desc(), StudySession.created_at.desc())
    ) if s.topic_ids]
    ids = [s.id for s in sessions]
    counts = {(sid, status): n for sid, status, n in db.execute(
        select(Flashcard.session_id, Flashcard.status, func.count())
        .where(Flashcard.session_id.in_(ids)).group_by(Flashcard.session_id, Flashcard.status))}
    generated = set(db.scalars(select(FlashcardBatch.session_id).where(FlashcardBatch.session_id.in_(ids))))
    return [(s, counts.get((s.id, "draft"), 0), counts.get((s.id, "approved"), 0), s.id in generated)
            for s in sessions]
