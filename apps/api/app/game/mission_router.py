import uuid
from datetime import date

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import get_db
from app.game import missions as service
from app.game.snapshot import tracked

router = APIRouter(tags=["missions"])


class OpenDayIn(BaseModel):
    occurrence_ids: list[uuid.UUID] = []
    review_ids: list[uuid.UUID] = []


class ItemPatch(BaseModel):
    na_reason: str | None = Field(default=None, max_length=200)


class CheckoutIn(BaseModel):
    note: str = Field(max_length=500)


@router.get("/days/{day}")
def get_day(day: date, db: Session = Depends(get_db), today: date = Depends(get_today)):
    return service.day_view(db, day, today)


@router.post("/days/{day}/mission")
def open_day(day: date, body: OpenDayIn, response: Response, db: Session = Depends(get_db),
             today: date = Depends(get_today)):
    def action():
        return service.open_day(db, day, today, body.occurrence_ids, body.review_ids)

    try:
        (mission, created), delta = tracked(db, today, action)
    except IntegrityError:
        # Outra requisição (clique duplo, outro aparelho) gravou o mesmo dia/semana: a segunda tentativa encontra o registro.
        db.rollback()
        (mission, created), delta = tracked(db, today, action)
    response.status_code = 201 if created else 200
    return {**service.mission_out(db, mission), "game_delta": delta}


@router.patch("/missions/{mission_id}/items/{item_id}")
def patch_item(mission_id: uuid.UUID, item_id: uuid.UUID, body: ItemPatch, db: Session = Depends(get_db),
               today: date = Depends(get_today)):
    mission, delta = tracked(db, today, lambda: service.set_item_na(db, mission_id, item_id, body.na_reason))
    return {**service.mission_out(db, mission), "game_delta": delta}


@router.put("/missions/{mission_id}/checkout")
def put_checkout(mission_id: uuid.UUID, body: CheckoutIn, db: Session = Depends(get_db),
                 today: date = Depends(get_today)):
    mission, delta = tracked(db, today, lambda: service.set_checkout(db, mission_id, body.note))
    return {**service.mission_out(db, mission), "game_delta": delta}
