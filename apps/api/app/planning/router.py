import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import get_db
from app.game.snapshot import tracked
from app.planning import service

router = APIRouter(tags=["planning"])


class WeekIn(BaseModel):
    week_start: date


class OccurrencePatch(BaseModel):
    version: int
    planned_on: date | None = None
    window: Literal["before", "middle", "after"] | None = None
    status: Literal["pending", "completed", "skipped"] | None = None
    skip_reason: str | None = None


@router.get("/plans/current")
def get_plan(db: Session = Depends(get_db)):
    plan = service.current_plan(db)
    return {
        "id": str(plan.id),
        "starts_on": plan.starts_on,
        "ends_on": plan.ends_on,
        "exam_date": plan.exam_version.exam_date,
        "templates": [
            {
                "id": str(t.id),
                "effective_from": t.effective_from,
                "weekly_minutes": t.weekly_minutes,
                "origin": t.origin,
                "slots": [
                    {"code": s.code, "weekday": s.weekday, "window": s.window, "minutes": s.minutes,
                     "purpose": s.purpose, "activity": s.activity, "title": s.title}
                    for s in t.slots
                ],
            }
            for t in sorted(service.templates(db, plan), key=lambda t: t.effective_from)
        ],
    }


@router.post("/plans/current/weeks")
def create_week(body: WeekIn, response: Response, db: Session = Depends(get_db),
                today: date = Depends(get_today)):
    def action():
        return service.ensure_week(db, body.week_start)

    try:
        (occurrences, created), delta = tracked(db, today, action)
    except IntegrityError:
        # Geração concorrente da mesma semana: a segunda tentativa devolve a semana já gravada.
        db.rollback()
        (occurrences, created), delta = tracked(db, today, action)
    response.status_code = 201 if created else 200
    return {"week_start": body.week_start, "items": service.occurrences_out(db, occurrences), "game_delta": delta}


@router.get("/occurrences")
def get_occurrences(from_: date = Query(alias="from"), to: date = Query(), db: Session = Depends(get_db)):
    items = service.occurrences_out(db, service.list_occurrences(db, from_, to))
    return {"items": items, "total": len(items)}


@router.patch("/occurrences/{occ_id}")
def update_occurrence(occ_id: uuid.UUID, body: OccurrencePatch, db: Session = Depends(get_db),
                      today: date = Depends(get_today)):
    occ, delta = tracked(db, today, lambda: service.patch_occurrence(db, occ_id, body.model_dump()))
    return {**service.occurrences_out(db, [occ])[0], "game_delta": delta}
