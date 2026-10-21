import uuid
from datetime import date

from sqlalchemy import select

from app.models import ReviewTask, SessionTopic, StudySession
from app.reviews.service import create_from_history

D = date.fromisoformat


def post_session(client, topic_ids=("C02.01",), studied_on="2026-10-09", activity="theory"):
    body = {"id": str(uuid.uuid4()), "studied_on": studied_on, "duration_minutes": 50, "activity": activity,
            "topic_ids": list(topic_ids), "notes": ""}
    r = client.post("/api/v1/sessions", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def reviews(db, status=None):
    db.expire_all()
    query = select(ReviewTask).order_by(ReviewTask.topic_id, ReviewTask.due_on)
    if status:
        query = query.where(ReviewTask.status == status)
    return [(r.topic_id, r.due_on, r.status) for r in db.scalars(query)]


def test_theory_session_creates_three_reviews(client, db):
    post_session(client)
    assert reviews(db) == [("C02.01", D("2026-10-10"), "pending"), ("C02.01", D("2026-10-16"), "pending"),
                           ("C02.01", D("2026-10-30"), "pending")]


def test_late_registration_keeps_overdue_reviews(client, db, clock):
    clock.today = D("2026-10-20")
    post_session(client)
    assert [d for _, d, _ in reviews(db)] == [D("2026-10-10"), D("2026-10-16"), D("2026-10-30")]


def test_same_topic_next_day_is_deduplicated(client, db):
    first = post_session(client, studied_on="2026-10-08")
    post_session(client, studied_on="2026-10-09")
    db.expire_all()
    rows = list(db.scalars(select(ReviewTask)))
    assert sorted(r.due_on for r in rows) == [D("2026-10-09"), D("2026-10-15"), D("2026-10-29")]
    assert {str(r.session_id) for r in rows} == {first["id"]}


def test_questions_session_creates_none(client, db):
    post_session(client, activity="questions")
    assert reviews(db) == []


def test_delete_and_edit_dismiss_pending(client, db):
    s = post_session(client)
    r = client.patch(f"/api/v1/sessions/{s['id']}", json={"version": s["version"], "topic_ids": ["C03.01"]})
    assert r.status_code == 200, r.text
    assert {(t, st) for t, _, st in reviews(db)} == {("C02.01", "dismissed"), ("C03.01", "pending")}
    assert client.delete(f"/api/v1/sessions/{s['id']}").status_code == 204
    assert {st for _, _, st in reviews(db)} == {"dismissed"}


def test_history_skips_past_due_dates(db):
    db.add(StudySession(id=uuid.uuid4(), studied_on=D("2026-10-09"), duration_minutes=60, activity="theory", notes="",
                        topic_links=[SessionTopic(topic_id="C02.01")]))
    db.flush()
    create_from_history(db, D("2026-10-20"))
    assert reviews(db) == [("C02.01", D("2026-10-30"), "pending")]
