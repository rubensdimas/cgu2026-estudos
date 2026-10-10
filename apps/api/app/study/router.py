import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import get_db
from app.game.snapshot import tracked
from app.study import service

router = APIRouter(tags=["sessions"])


@router.post("/sessions")
def create_session(body: service.SessionIn, response: Response, db: Session = Depends(get_db),
                   today: date = Depends(get_today)):
    def action():
        return service.create_session(db, body, today)

    try:
        (session, created), delta = tracked(db, today, action)
    except IntegrityError:
        # Mesmo id gravado por outra requisição em paralelo: a segunda tentativa aplica a regra de idempotência.
        db.rollback()
        (session, created), delta = tracked(db, today, action)
    response.status_code = 201 if created else 200
    return {**service.session_out(session), "game_delta": delta}


@router.patch("/sessions/{session_id}")
def update_session(session_id: uuid.UUID, body: service.SessionPatch, db: Session = Depends(get_db),
                   today: date = Depends(get_today)):
    session, delta = tracked(db, today, lambda: service.update_session(db, session_id, body, today))
    return {**service.session_out(session), "game_delta": delta}


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: uuid.UUID, db: Session = Depends(get_db), today: date = Depends(get_today)):
    tracked(db, today, lambda: service.delete_session(db, session_id))
    return Response(status_code=204)


@router.get("/sessions")
def list_sessions(
    from_: date = Query(alias="from"), to: date = Query(),
    limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    rows, total = service.list_sessions(db, from_, to, limit, offset)
    return {"items": [service.session_out(s) for s in rows], "total": total, "limit": limit, "offset": offset}
