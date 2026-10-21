import uuid
from datetime import date

from sqlalchemy import select

from app.models import Flashcard, ReviewTask, SessionTopic, StudySession
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


def listed(client, start="2026-10-01", end="2026-11-30"):
    return client.get("/api/v1/reviews", params={"from": start, "to": end}).json()["items"]


def test_complete_closes_overdue_same_topic_and_scores_once(client, db, clock):
    post_session(client, studied_on="2026-10-09")              # vence 10/10, 16/10, 30/10
    clock.today = D("2026-10-20")
    post_session(client, studied_on="2026-10-19")              # 20/10 (26/10 e 09/11 também)
    items = listed(client)
    today = next(r for r in items if r["due_on"] == "2026-10-20")
    assert sum(r["late"] for r in items) == 2
    r = client.post(f"/api/v1/reviews/{today['id']}/complete", json={})
    assert r.status_code == 200, r.text
    assert r.json()["game_delta"]["xp_gained"] == 15
    states = {i["due_on"]: i["status"] for i in listed(client)}
    assert states["2026-10-10"] == states["2026-10-16"] == states["2026-10-20"] == "completed"
    assert states["2026-10-30"] == "pending"


def test_complete_late_scores_five_and_only_once(client, clock):
    post_session(client)
    clock.today = D("2026-10-20")
    first = listed(client)[0]
    r = client.post(f"/api/v1/reviews/{first['id']}/complete", json={})
    assert r.json()["game_delta"]["xp_gained"] == 5
    again = client.post(f"/api/v1/reviews/{first['id']}/complete", json={})
    assert (again.status_code, again.json()["error"]["code"]) == (422, "not_pending")


def test_dismiss_and_list_buckets(client, clock):
    post_session(client)
    clock.today = D("2026-10-20")
    items = listed(client, "2026-10-20", "2026-11-03")
    assert [(i["due_on"], i["late"]) for i in items] == [("2026-10-10", True), ("2026-10-16", True), ("2026-10-30", False)]
    client.post(f"/api/v1/reviews/{items[0]['id']}/dismiss", json={})
    assert [i["status"] for i in listed(client, "2026-10-20", "2026-11-03")] == ["pending", "pending"]


def test_review_detail_orders_cards_and_rates(client, db):
    s = post_session(client)
    cards = [Flashcard(session_id=uuid.UUID(s["id"]), topic_id="C02.01", subitem="1.1", category="conceito",
                       front=f"F{i}", back="V", status="approved") for i in range(3)]
    draft = Flashcard(session_id=uuid.UUID(s["id"]), topic_id="C02.01", subitem="1.1", category="conceito",
                      front="rascunho", back="V", status="draft")
    db.add_all([*cards, draft])
    db.commit()
    assert client.put(f"/api/v1/flashcards/{cards[0].id}/rating", json={"rating": "lembrei"}).status_code == 200
    rated = client.put(f"/api/v1/flashcards/{cards[2].id}/rating", json={"rating": "nao_lembrei"}).json()
    assert rated["last_rating"] == "nao_lembrei"
    assert client.put(f"/api/v1/flashcards/{draft.id}/rating", json={"rating": "lembrei"}).status_code == 422
    review = listed(client)[0]
    assert review["cards_count"] == 3
    detail = client.get(f"/api/v1/reviews/{review['id']}").json()
    assert [c["front"] for c in detail["cards"]] == ["F2", "F1", "F0"]
