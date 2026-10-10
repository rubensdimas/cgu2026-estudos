from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.clock import get_today
from app.db import get_db
from app.errors import ApiError
from app.models import AppSettings, ExamVersion, Subject, Topic, TopicProgress

router = APIRouter(tags=["catalog"])


class ProgressIn(BaseModel):
    status: Literal["not_started", "in_progress", "first_pass", "reviewed"]
    version: int | None = None


def progress_out(p: TopicProgress | None) -> dict | None:
    if p is None:
        return None
    return {"status": p.status, "declared_on": p.declared_on, "version": p.version}


@router.get("/exam-versions/current")
def current_exam_version(db: Session = Depends(get_db)):
    ev = db.scalar(select(ExamVersion).order_by(ExamVersion.publication_date.desc()).limit(1))
    if ev is None:
        raise ApiError(404, "not_found", "Versão do edital não carregada.")
    return {"id": ev.id, "title": ev.title, "publication_date": ev.publication_date, "source_url": ev.source_url,
            "source_sha256": ev.source_sha256, "exam_date": ev.exam_date, "scoring_rules": ev.scoring_rules}


@router.get("/subjects")
def list_subjects(db: Session = Depends(get_db)):
    progress = {p.topic_id: p for p in db.scalars(select(TopicProgress))}
    subjects = db.scalars(select(Subject).options(selectinload(Subject.topics)).order_by(Subject.position))
    items = [
        {"id": s.id, "paper": s.paper, "title": s.title, "source_ref": s.source_ref,
         "topics": [{"id": t.id, "title": t.title, "source_ref": t.source_ref,
                     "progress": progress_out(progress.get(t.id))} for t in s.topics]}
        for s in subjects
    ]
    return {"items": items, "total": len(items)}


@router.put("/topics/{topic_id}/progress")
def put_progress(topic_id: str, body: ProgressIn, db: Session = Depends(get_db), today: date = Depends(get_today)):
    if db.get(Topic, topic_id) is None:
        raise ApiError(404, "not_found", "Tópico não encontrado.")
    row = db.get(TopicProgress, topic_id)
    if row is None:
        row = TopicProgress(topic_id=topic_id, status=body.status, declared_on=today)
        db.add(row)
    else:
        if body.version != row.version:
            raise ApiError(409, "version_conflict", "Este registro foi alterado. Recarregue antes de editar.")
        row.status, row.declared_on = body.status, today
        row.version += 1
    db.commit()
    return {"topic_id": topic_id, **progress_out(row)}


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    s = db.get(AppSettings, 1)
    return {"timezone": s.timezone, "weekly_goals": s.weekly_goals, "daily_question_goal": s.daily_question_goal,
            "streak_min_minutes": s.streak_min_minutes, "max_freezes": s.max_freezes, "version": s.version}
