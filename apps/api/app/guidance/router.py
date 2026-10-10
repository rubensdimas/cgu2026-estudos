import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import ApiError
from app.guidance import service
from app.models import Occurrence

router = APIRouter(tags=["guidance"])


@router.get("/occurrences/{occ_id}/guidance")
def get_guidance(occ_id: uuid.UUID, db: Session = Depends(get_db)):
    occ = db.get(Occurrence, occ_id)
    if occ is None:
        raise ApiError(404, "not_found", "Bloco não encontrado.")
    return service.guidance_out(db, occ)
