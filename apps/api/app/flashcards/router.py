import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.flashcards import service
from app.flashcards.ai import Generator, get_generator
from app.study.service import session_out

router = APIRouter(tags=["flashcards"])


class GenerateIn(BaseModel):
    studied: str = Field(default="", max_length=4000)


class CardPatch(BaseModel):
    version: int
    front: str | None = Field(default=None, min_length=1, max_length=2000)
    back: str | None = Field(default=None, min_length=1, max_length=2000)
    status: Literal["approved"] | None = None


@router.get("/flashcards/status")
def status(generator: Generator | None = Depends(get_generator)):
    return {"enabled": generator is not None, "model": config.OPENAI_MODEL}


@router.get("/flashcards/sessions")
def list_sessions(from_: date = Query(alias="from"), to: date = Query(), db: Session = Depends(get_db)):
    rows = service.theory_sessions(db, from_, to)
    items = [{"session": session_out(s), "drafts": d, "approved": a, "generated": g} for s, d, a, g in rows]
    return {"items": items, "total": len(items)}


@router.get("/flashcards")
def list_deck(topic_id: str | None = None, db: Session = Depends(get_db)):
    items = [service.card_out(c) for c in service.deck(db, topic_id)]
    return {"items": items, "total": len(items)}


@router.get("/sessions/{session_id}/flashcards")
def get_session_flashcards(session_id: uuid.UUID, db: Session = Depends(get_db)):
    return service.session_flashcards(db, session_id)


@router.post("/sessions/{session_id}/flashcards", status_code=201)
def generate(session_id: uuid.UUID, body: GenerateIn, db: Session = Depends(get_db),
             generator: Generator | None = Depends(get_generator)):
    result = service.generate(db, session_id, body.studied, generator)
    db.commit()
    return result


@router.post("/sessions/{session_id}/flashcards/approve")
def approve_all(session_id: uuid.UUID, db: Session = Depends(get_db)):
    result = service.approve_all(db, session_id)
    db.commit()
    return result


@router.patch("/flashcards/{card_id}")
def patch_card(card_id: uuid.UUID, body: CardPatch, db: Session = Depends(get_db)):
    card = service.patch_card(db, card_id, body.version, body.model_dump(exclude={"version"}))
    db.commit()
    return service.card_out(card)


@router.delete("/flashcards/{card_id}", status_code=204)
def delete_card(card_id: uuid.UUID, db: Session = Depends(get_db)):
    service.delete_card(db, card_id)
    db.commit()
    return Response(status_code=204)
