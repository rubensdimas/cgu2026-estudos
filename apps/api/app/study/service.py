import uuid
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalog.progress import promote_for_occurrence, promote_for_session
from app.errors import ApiError
from app.guidance.service import current_theme
from app.models import Occurrence, SessionTopic, StudySession, Topic
from app.reviews.service import create_for_session, dismiss_for_session

Activity = Literal["theory", "questions", "review", "essay"]
EssayKind = Literal["complementary", "technical_case"]


class SessionIn(BaseModel):
    id: uuid.UUID
    occurrence_id: uuid.UUID | None = None
    studied_on: date
    duration_minutes: int = Field(ge=1, le=720)
    activity: Activity
    essay_kind: EssayKind | None = None
    topic_ids: list[str] = []
    notes: str = Field(default="", max_length=2000)
    complete_occurrence: bool = False

    @model_validator(mode="after")
    def check_activity(self):
        if self.activity == "essay" and self.essay_kind is None:
            raise ValueError("Discursiva exige essay_kind.")
        if self.activity != "essay" and not self.topic_ids:
            raise ValueError("Informe ao menos um tópico.")
        if self.activity != "essay" and self.essay_kind is not None:
            raise ValueError("essay_kind só vale para discursiva.")
        return self


class SessionPatch(BaseModel):
    version: int
    studied_on: date | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=720)
    topic_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=2000)


def _fingerprint(occurrence_id, studied_on, minutes, activity, essay_kind, topic_ids, notes) -> tuple:
    return (
        str(occurrence_id) if occurrence_id else None, studied_on, minutes, activity, essay_kind,
        tuple(sorted(set(topic_ids))), notes,
    )


def _check_not_future(studied_on: date, today: date) -> None:
    if studied_on > today:
        raise ApiError(422, "future_date", "A data do estudo não pode ser futura.", {"studied_on": "Data futura."})


def _check_topics(db: Session, topic_ids: list[str]) -> None:
    wanted = set(topic_ids)
    found = set(db.scalars(select(Topic.id).where(Topic.id.in_(wanted))))
    missing = sorted(wanted - found)
    if missing:
        raise ApiError(422, "unknown_topic", "Tópico inexistente.", {"topic_ids": ", ".join(missing)})


def active_minutes(db: Session, occurrence_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.coalesce(func.sum(StudySession.duration_minutes), 0)).where(
            StudySession.occurrence_id == occurrence_id, StudySession.deleted_at.is_(None)
        )
    )


def session_out(s: StudySession) -> dict:
    return {
        "id": str(s.id),
        "version": s.version,
        "occurrence_id": str(s.occurrence_id) if s.occurrence_id else None,
        "studied_on": s.studied_on,
        "duration_minutes": s.duration_minutes,
        "activity": s.activity,
        "essay_kind": s.essay_kind,
        "topic_ids": s.topic_ids,
        "notes": s.notes,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


def create_session(db: Session, data: SessionIn, today: date) -> tuple[StudySession, bool]:
    existing = db.get(StudySession, data.id)
    if existing is not None:
        same = _fingerprint(
            existing.occurrence_id, existing.studied_on, existing.duration_minutes, existing.activity,
            existing.essay_kind, existing.topic_ids, existing.notes,
        ) == _fingerprint(
            data.occurrence_id, data.studied_on, data.duration_minutes, data.activity, data.essay_kind,
            data.topic_ids, data.notes,
        )
        if same:
            return existing, False
        raise ApiError(409, "duplicate_id_conflict", "Já existe um registro com este id e conteúdo diferente.")
    _check_not_future(data.studied_on, today)
    _check_topics(db, data.topic_ids)
    occurrence = None
    if data.occurrence_id is not None:
        occurrence = db.get(Occurrence, data.occurrence_id)
        if occurrence is None:
            raise ApiError(422, "unknown_occurrence", "Bloco inexistente.", {"occurrence_id": "Inexistente."})
        if occurrence.status == "skipped":
            raise ApiError(422, "occurrence_skipped", "Bloco dispensado: reabra antes de registrar.")
    if occurrence is not None and occurrence.theme_id is None and occurrence.slot.activity == "essay":
        # Fixa o tema exibido antes que esta sessão o marque como feito e mude o rodízio.
        occurrence.theme_id = current_theme(db, occurrence)
    session = StudySession(
        id=data.id,
        occurrence_id=data.occurrence_id,
        studied_on=data.studied_on,
        duration_minutes=data.duration_minutes,
        activity=data.activity,
        essay_kind=data.essay_kind,
        notes=data.notes,
        topic_links=[SessionTopic(topic_id=t) for t in sorted(set(data.topic_ids))],
    )
    db.add(session)
    db.flush()
    if data.complete_occurrence and occurrence is not None and occurrence.status == "pending":
        occurrence.status = "completed"
        occurrence.version += 1
        db.flush()
        promote_for_occurrence(db, occurrence)
    else:
        promote_for_session(db, session)
    create_for_session(db, session)
    return session, True


def update_session(db: Session, session_id: uuid.UUID, patch: SessionPatch, today: date) -> StudySession:
    session = db.get(StudySession, session_id)
    if session is None or session.deleted_at is not None:
        raise ApiError(404, "not_found", "Sessão não encontrada.")
    if patch.version != session.version:
        raise ApiError(409, "version_conflict", "Este registro foi alterado. Recarregue antes de editar.")
    if patch.studied_on is not None:
        _check_not_future(patch.studied_on, today)
        session.studied_on = patch.studied_on
    if patch.duration_minutes is not None:
        session.duration_minutes = patch.duration_minutes
    if patch.notes is not None:
        session.notes = patch.notes
    if patch.topic_ids is not None:
        if session.activity != "essay" and not patch.topic_ids:
            raise ApiError(422, "topic_required", "Informe ao menos um tópico.", {"topic_ids": "Obrigatório."})
        _check_topics(db, patch.topic_ids)
        added = set(patch.topic_ids) - set(session.topic_ids)
        removed = set(session.topic_ids) - set(patch.topic_ids)
        session.topic_links = [SessionTopic(topic_id=t) for t in sorted(set(patch.topic_ids))]
    session.version += 1
    db.flush()
    if patch.topic_ids is not None:
        promote_for_session(db, session, added)
        dismiss_for_session(db, session.id, removed)
        create_for_session(db, session, added)
    return session


def delete_session(db: Session, session_id: uuid.UUID) -> None:
    session = db.get(StudySession, session_id)
    if session is None:
        raise ApiError(404, "not_found", "Sessão não encontrada.")
    if session.deleted_at is not None:
        return
    session.deleted_at = datetime.now(timezone.utc)
    session.version += 1
    db.flush()
    dismiss_for_session(db, session.id)
    if session.occurrence_id is not None:
        occurrence = db.get(Occurrence, session.occurrence_id)
        if occurrence.status == "completed" and active_minutes(db, occurrence.id) == 0:
            occurrence.status = "pending"
            occurrence.version += 1
            db.flush()


def list_sessions(db: Session, start: date, end: date, limit: int, offset: int) -> tuple[list[StudySession], int]:
    where = (StudySession.deleted_at.is_(None), StudySession.studied_on.between(start, end))
    total = db.scalar(select(func.count()).select_from(StudySession).where(*where))
    rows = db.scalars(
        select(StudySession).where(*where)
        .order_by(StudySession.studied_on.desc(), StudySession.created_at.desc())
        .limit(limit).offset(offset)
    )
    return list(rows), total
