import uuid

import pytest

from app.flashcards.ai import AiError, get_generator
from app.flashcards.domain import Batch, Card
from app.main import app


class FakeGenerator:
    model = "fake-model"

    def __init__(self):
        self.ctx, self.error = None, None

    def __call__(self, ctx):
        self.ctx = ctx
        if self.error:
            raise self.error
        cards = [Card("conceito", "1.1", f"Frente {i}?", f"Verso {i}.") for i in range(2)]
        return Batch("observação", "foco", ["prazo"], cards + [Card("distincao", "1.2", "Frente 2?", "Verso 2.")])


@pytest.fixture
def fake(client):
    gen = FakeGenerator()
    app.dependency_overrides[get_generator] = lambda: gen
    return gen


def post_session(client, activity="theory", topic_ids=("C02.01",), notes="LAI"):
    body = {"id": str(uuid.uuid4()), "studied_on": "2026-10-09", "duration_minutes": 50, "activity": activity,
            "topic_ids": list(topic_ids), "notes": notes}
    r = client.post("/api/v1/sessions", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def generate(client, session_id, studied="LAI e recursos"):
    return client.post(f"/api/v1/sessions/{session_id}/flashcards", json={"studied": studied})


def test_generate_creates_drafts_with_edital_context(client, fake):
    s = post_session(client)
    r = generate(client, s["id"])
    assert r.status_code == 201, r.text
    body = r.json()
    assert [c["status"] for c in body["cards"]] == ["draft"] * 3
    assert body["batch"]["model"] == "fake-model" and body["batch"]["priorities"] == ["prazo"]
    assert fake.ctx.topic_id == "C02.01" and fake.ctx.studied == "LAI e recursos"
    assert [x[:3] for x in fake.ctx.subitems] == ["1.1", "1.2"]
    assert len(fake.ctx.materials) == 2


def test_generate_rejects_non_theory_and_missing_key(client, fake):
    q = post_session(client, activity="questions")
    assert generate(client, q["id"]).json()["error"]["code"] == "not_theory"
    app.dependency_overrides[get_generator] = lambda: None
    s = post_session(client)
    r = generate(client, s["id"])
    assert (r.status_code, r.json()["error"]["code"]) == (503, "ai_disabled")
    assert client.get("/api/v1/flashcards/status").json()["enabled"] is False


def test_ai_failure_saves_nothing(client, fake):
    fake.error = AiError()
    s = post_session(client)
    r = generate(client, s["id"])
    assert (r.status_code, r.json()["error"]["code"]) == (502, "ai_failed")
    assert client.get(f"/api/v1/sessions/{s['id']}/flashcards").json() == {"batch": None, "cards": []}


def test_regenerate_replaces_drafts_keeps_approved(client, fake):
    s = post_session(client)
    first = generate(client, s["id"]).json()["cards"][0]
    client.patch(f"/api/v1/flashcards/{first['id']}", json={"version": first["version"], "status": "approved"})
    cards = generate(client, s["id"]).json()["cards"]
    assert [c["status"] for c in cards].count("approved") == 1
    assert [c["status"] for c in cards].count("draft") == 3
    assert first["id"] in [c["id"] for c in cards]


def test_edit_approve_all_discard_and_deck(client, fake):
    s = post_session(client)
    a, b, c = generate(client, s["id"]).json()["cards"]
    edited = client.patch(f"/api/v1/flashcards/{a['id']}", json={"version": a["version"], "front": "Nova frente?"})
    assert edited.json()["front"] == "Nova frente?"
    stale = client.patch(f"/api/v1/flashcards/{a['id']}", json={"version": a["version"], "back": "x"})
    assert stale.status_code == 409
    assert client.delete(f"/api/v1/flashcards/{b['id']}").status_code == 204
    approved = client.post(f"/api/v1/sessions/{s['id']}/flashcards/approve", json={}).json()["cards"]
    assert [x["status"] for x in approved] == ["approved", "approved"]
    deck = client.get("/api/v1/flashcards", params={"topic_id": "C02.01"}).json()
    assert deck["total"] == 2 and deck["items"][0]["front"] == "Nova frente?"


def test_deleted_session_keeps_deck_and_blocks_generation(client, fake):
    s = post_session(client)
    generate(client, s["id"])
    client.post(f"/api/v1/sessions/{s['id']}/flashcards/approve", json={})
    assert client.delete(f"/api/v1/sessions/{s['id']}").status_code == 204
    assert client.get("/api/v1/flashcards").json()["total"] == 3
    assert generate(client, s["id"]).status_code == 404


def test_studied_text_limits(client, fake):
    s = post_session(client)
    text = ('Prazo "20 dias"\nrecurso ' * 100)[:2000]
    assert generate(client, s["id"], text).status_code == 201
    assert fake.ctx.studied == text
    assert generate(client, s["id"], "x" * 4001).status_code == 422


def test_sessions_listing_counts(client, fake):
    done = post_session(client)
    post_session(client, topic_ids=("C03.01",))
    post_session(client, activity="questions")
    generate(client, done["id"])
    items = client.get("/api/v1/flashcards/sessions", params={"from": "2026-10-01", "to": "2026-10-09"}).json()["items"]
    by_id = {i["session"]["id"]: i for i in items}
    assert len(items) == 2
    assert (by_id[done["id"]]["generated"], by_id[done["id"]]["drafts"], by_id[done["id"]]["approved"]) == (True, 3, 0)
    assert [i["generated"] for i in items].count(False) == 1
