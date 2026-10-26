from sqlalchemy import func, select

from app.models import AppSettings, CycleSlot, CycleTemplate, StudyPlan, Subject, Topic
from app.seed import seed


def counts(db):
    return {
        "subjects": db.scalar(select(func.count()).select_from(Subject)),
        "topics": db.scalar(select(func.count()).select_from(Topic)),
        "plans": db.scalar(select(func.count()).select_from(StudyPlan)),
        "templates": db.scalar(select(func.count()).select_from(CycleTemplate)),
        "slots": db.scalar(select(func.count()).select_from(CycleSlot)),
        "minutes": db.scalar(select(func.sum(CycleSlot.minutes))),
    }


def test_seed_is_idempotent(db):
    expected = {"subjects": 13, "topics": 68, "plans": 1, "templates": 2, "slots": 20, "minutes": 1200}
    assert counts(db) == expected
    seed(db)
    assert counts(db) == expected


def test_seed_never_overwrites_settings(db):
    settings = db.get(AppSettings, 1)
    settings.streak_min_minutes = 45
    db.commit()
    seed(db)
    db.expire_all()
    assert db.get(AppSettings, 1).streak_min_minutes == 45


def test_seed_updates_slot_titles(db):
    slot = db.scalar(select(CycleSlot).where(CycleSlot.code == "S13"))
    assert slot.title == "Complementares + revisão da semana"
    slot.title = "antigo"
    db.commit()
    seed(db)
    db.expire_all()
    assert db.scalar(select(CycleSlot).where(CycleSlot.code == "S13")).title == "Complementares + revisão da semana"
