import uuid
from datetime import date

import pytest
from sqlalchemy import delete, select

from app.models import AppSettings, CycleSlot, CycleTemplate, Occurrence, ReviewTask
from app.replan import SKIP_REASON, replan

D = date.fromisoformat
TODAY = D("2026-10-26")


def session(client, studied_on, topic, activity="theory", occurrence_id=None):
    body = {"id": str(uuid.uuid4()), "studied_on": studied_on, "duration_minutes": 60, "activity": activity,
            "topic_ids": [topic], "notes": "", "occurrence_id": occurrence_id}
    r = client.post("/api/v1/sessions", json=body)
    assert r.status_code == 201, r.text


@pytest.fixture
def history(client, db, clock):
    """Reproduz o banco real de 26/10: 6 tópicos estudados e a semana de 19/10 parada no dia 20."""
    clock.today = TODAY
    session(client, "2026-10-10", "C04.01")
    session(client, "2026-10-14", "B03.01")
    session(client, "2026-10-14", "E03.01")
    session(client, "2026-10-15", "C03.01")
    items = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-19"}).json()["items"]
    tuesday = {i["window"]: i for i in items if i["planned_on"] == "2026-10-20"}
    session(client, "2026-10-20", "C02.01", occurrence_id=tuesday["before"]["id"])
    session(client, "2026-10-20", "E02.01", "questions", tuesday["middle"]["id"])
    session(client, "2026-10-20", "E02.01", occurrence_id=tuesday["after"]["id"])
    for occ in tuesday.values():
        r = client.patch(f"/api/v1/occurrences/{occ['id']}", json={"version": occ["version"], "status": "completed"})
        assert r.status_code == 200, r.text
    # No banco real, C04.01 só tem a revisão de 21 dias (as anteriores já tinham passado na implantação).
    db.execute(delete(ReviewTask).where(ReviewTask.topic_id == "C04.01", ReviewTask.offset_days.in_((1, 7))))
    db.commit()


def schedule(db):
    db.expire_all()
    rows = db.scalars(select(ReviewTask).where(ReviewTask.status == "pending"))
    out: dict[str, dict[int, date]] = {}
    for r in rows:
        out.setdefault(r.topic_id, {})[r.offset_days] = r.due_on
    return out


def snapshot(db):
    db.expire_all()
    return (sorted((str(r.id), r.status, r.due_on, r.version) for r in db.scalars(select(ReviewTask))),
            sorted((str(o.id), o.status, o.version) for o in db.scalars(select(Occurrence))))


def test_replan_real_scenario(history, db):
    result = replan(db, TODAY)
    db.commit()
    assert result == {"blocks_skipped": 12, "reviews_rescheduled": 16, "reviews_created": 2,
                      "reviews_dismissed": 0, "week_generated": True}
    occs = list(db.scalars(select(Occurrence).where(Occurrence.week_start == D("2026-10-19"))))
    assert sorted(o.status for o in occs) == ["completed"] * 3 + ["skipped"] * 12
    assert {o.skip_reason for o in occs if o.status == "skipped"} == {SKIP_REASON}
    sat = {1: D("2026-10-31"), 7: D("2026-11-07"), 21: D("2026-11-21")}
    sun = {1: D("2026-11-01"), 7: D("2026-11-08"), 21: D("2026-11-22")}
    assert schedule(db) == {"C04.01": sat, "B03.01": sat, "E03.01": sat, "C03.01": sun, "C02.01": sun, "E02.01": sun}
    codes = db.scalars(select(CycleSlot.code).join(Occurrence).where(Occurrence.week_start == TODAY))
    assert sorted(codes) == ["T01", "T02", "T03", "T04", "T05"]
    settings = db.get(AppSettings, 1)
    assert settings.daily_question_goal == 10
    assert settings.weekly_goals == {"minutes": 300, "blocks": 5, "questions": {"P1": 15, "P2": 15, "P3": 30},
                                     "essays": {"per_week": 1}, "missions": 5}


def test_replan_is_idempotent(history, db):
    replan(db, TODAY)
    db.commit()
    before = snapshot(db)
    assert replan(db, TODAY) == {"blocks_skipped": 0, "reviews_rescheduled": 0, "reviews_created": 0,
                                 "reviews_dismissed": 0, "week_generated": False}
    db.commit()
    assert snapshot(db) == before


def test_replan_keeps_completed_review(history, client, db):
    review = db.scalar(select(ReviewTask).where(ReviewTask.topic_id == "C02.01", ReviewTask.offset_days == 1))
    assert client.post(f"/api/v1/reviews/{review.id}/complete", json={}).status_code == 200
    db.expire_all()
    replan(db, TODAY)
    db.commit()
    db.expire_all()
    kept = db.get(ReviewTask, review.id)
    assert (kept.status, kept.due_on) == ("completed", D("2026-10-21"))
    assert 1 not in schedule(db)["C02.01"]


def test_replan_dismisses_reviews_of_older_sessions(history, client, db):
    session(client, "2026-10-22", "C03.01")  # segunda sessão: a cadeia antiga do tópico sai
    replan(db, TODAY)
    db.commit()
    db.expire_all()
    pending = db.scalars(select(ReviewTask).where(ReviewTask.topic_id == "C03.01", ReviewTask.status == "pending"))
    assert len({r.session_id for r in pending}) == 1


def test_replan_aborts_on_old_template_week(history, db):
    old = db.scalar(select(CycleTemplate).where(CycleTemplate.effective_from == D("2026-10-05")))
    db.add(Occurrence(cycle_slot_id=old.slots[0].id, week_start=TODAY, planned_on=TODAY, window="before"))
    db.commit()
    before = snapshot(db)
    with pytest.raises(RuntimeError, match="semana de 26/10"):
        replan(db, TODAY)
    db.rollback()
    assert snapshot(db) == before
