import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import get_db
from app.game.missions import due_reviews
from app.game.snapshot import tracked
from app.reviews import service

router = APIRouter(tags=["reviews"])


@router.get("/reviews")
def list_reviews(from_: date = Query(alias="from"), to: date = Query(), db: Session = Depends(get_db),
                 today: date = Depends(get_today)):
    items = service.list_reviews(db, from_, to, today)
    return {"items": items, "total": len(items)}


@router.get("/reviews/due")
def due(day: date, db: Session = Depends(get_db), today: date = Depends(get_today)):
    counts = service.card_counts(db)
    items = [service.review_out(r, today, counts.get(r.topic_id, 0)) for r in due_reviews(db, day)]
    return {"items": items, "total": len(items)}


@router.get("/reviews/{review_id}")
def get_review(review_id: uuid.UUID, db: Session = Depends(get_db), today: date = Depends(get_today)):
    return service.review_detail(db, review_id, today)


def _mutation(db: Session, today: date, action) -> dict:
    review, delta = tracked(db, today, action)
    return {**service.review_out(review, today, len(service.approved_cards(db, review.topic_id))), "game_delta": delta}


@router.post("/reviews/{review_id}/complete")
def complete(review_id: uuid.UUID, db: Session = Depends(get_db), today: date = Depends(get_today)):
    return _mutation(db, today, lambda: service.complete(db, review_id, today))


@router.post("/reviews/{review_id}/dismiss")
def dismiss(review_id: uuid.UUID, db: Session = Depends(get_db), today: date = Depends(get_today)):
    return _mutation(db, today, lambda: service.dismiss(db, review_id))
