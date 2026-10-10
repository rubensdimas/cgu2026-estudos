from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import get_db
from app.errors import ApiError
from app.game import config as game_config
from app.game import snapshot
from app.game.snapshot import tracked
from app.models import DayOff

router = APIRouter(tags=["game"])


class DayOffIn(BaseModel):
    reason: str = Field(min_length=1, max_length=100)


@router.get("/game/summary")
def get_summary(db: Session = Depends(get_db), today: date = Depends(get_today)):
    return snapshot.summary(db, today)


@router.get("/game/xp")
def get_xp(from_: date = Query(alias="from"), to: date = Query(), db: Session = Depends(get_db),
           today: date = Depends(get_today)):
    items = snapshot.ledger(db, today, from_, to)
    return {"items": items, "total": len(items)}


@router.get("/game/calendar")
def get_calendar(from_: date = Query(alias="from"), to: date = Query(), db: Session = Depends(get_db),
                 today: date = Depends(get_today)):
    if to < from_ or (to - from_).days > 400:
        raise ApiError(422, "invalid_range", "Intervalo inválido (máximo de 400 dias).")
    return snapshot.calendar(db, today, from_, to)


@router.get("/game/config")
def get_config():
    cfg = game_config.game_config()
    return {"holiday_suggestions": cfg.get("holiday_suggestions", []), "milestones": cfg["milestones"],
            "levels": cfg["levels"]["titles"]}


@router.get("/day-offs")
def list_day_offs(db: Session = Depends(get_db)):
    rows = db.scalars(select(DayOff).order_by(DayOff.day))
    items = [{"day": r.day, "reason": r.reason} for r in rows]
    return {"items": items, "total": len(items)}


@router.put("/day-offs/{day}")
def put_day_off(day: date, body: DayOffIn, db: Session = Depends(get_db), today: date = Depends(get_today)):
    if day.weekday() >= 5:
        raise ApiError(422, "weekend", "Fim de semana já é neutro para a sequência.")

    def action():
        row = db.get(DayOff, day) or DayOff(day=day)
        row.reason = body.reason
        db.add(row)
        return row

    row, delta = tracked(db, today, action)
    return {"day": row.day, "reason": row.reason, "game_delta": delta}


@router.delete("/day-offs/{day}", status_code=204)
def delete_day_off(day: date, db: Session = Depends(get_db), today: date = Depends(get_today)):
    def action():
        row = db.get(DayOff, day)
        if row is not None:
            db.delete(row)

    tracked(db, today, action)
    return Response(status_code=204)
