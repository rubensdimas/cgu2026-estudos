import uuid


def friday_blocks(client):
    return client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-05"}).json()["items"]


def friday_occurrence(client, occ_id):
    items = client.get("/api/v1/occurrences", params={"from": "2026-10-09", "to": "2026-10-09"}).json()["items"]
    return next(o for o in items if o["id"] == occ_id)


def payload(**over):
    body = {"id": str(uuid.uuid4()), "studied_on": "2026-10-09", "duration_minutes": 50,
            "activity": "theory", "topic_ids": ["C02.01", "C04.01"], "notes": "LAI"}
    body.update(over)
    return body


def test_create_session_counts_minutes_once_and_completes_block(client):
    occ = friday_blocks(client)[0]
    r = client.post("/api/v1/sessions", json=payload(occurrence_id=occ["id"], complete_occurrence=True))
    assert r.status_code == 201
    assert r.json()["topic_ids"] == ["C02.01", "C04.01"]
    assert r.json()["game_delta"]["xp_gained"] == 50 + 20
    first = friday_occurrence(client, occ["id"])
    assert (first["status"], first["actual_minutes"], first["completed_on"]) == ("completed", 50, "2026-10-09")


def test_resend_same_id_is_idempotent_and_conflict_on_different_payload(client):
    body = payload()
    assert client.post("/api/v1/sessions", json=body).status_code == 201
    again = client.post("/api/v1/sessions", json=body)
    assert again.status_code == 200
    assert again.json()["game_delta"]["xp_gained"] == 0
    listed = client.get("/api/v1/sessions", params={"from": "2026-10-01", "to": "2026-10-31"}).json()
    assert listed["total"] == 1
    conflict = client.post("/api/v1/sessions", json={**body, "duration_minutes": 51})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "duplicate_id_conflict"


def test_validation(client, clock):
    assert client.post("/api/v1/sessions", json=payload(duration_minutes=0)).status_code == 422
    assert client.post("/api/v1/sessions", json=payload(duration_minutes=721)).status_code == 422
    assert client.post("/api/v1/sessions", json=payload(topic_ids=[])).status_code == 422
    assert client.post("/api/v1/sessions", json=payload(topic_ids=["X99.99"])).status_code == 422
    future = client.post("/api/v1/sessions", json=payload(studied_on="2026-10-10"))
    assert future.status_code == 422
    assert future.json()["error"]["fields"] == {"studied_on": "Data futura."}


def test_essay_session_without_topics(client):
    essay_block = friday_blocks(client)[1]
    r = client.post("/api/v1/sessions", json=payload(
        occurrence_id=essay_block["id"], activity="essay", essay_kind="complementary", topic_ids=[],
        complete_occurrence=True))
    assert r.status_code == 201
    no_kind = client.post("/api/v1/sessions", json=payload(activity="essay", topic_ids=[]))
    assert no_kind.status_code == 422


def test_edit_with_version_and_delete_reopens_block(client):
    occ = friday_blocks(client)[0]
    created = client.post("/api/v1/sessions", json=payload(occurrence_id=occ["id"], complete_occurrence=True)).json()
    edited = client.patch(f"/api/v1/sessions/{created['id']}", json={"version": created["version"], "duration_minutes": 40})
    assert edited.status_code == 200
    assert edited.json()["game_delta"]["xp_gained"] == -10
    stale = client.patch(f"/api/v1/sessions/{created['id']}", json={"version": created["version"], "notes": "x"})
    assert stale.status_code == 409
    assert client.delete(f"/api/v1/sessions/{created['id']}").status_code == 204
    assert friday_occurrence(client, occ["id"])["status"] == "pending"


def test_studied_on_is_kept_as_sent(client, clock):
    from datetime import date
    clock.today = date(2026, 10, 12)
    created = client.post("/api/v1/sessions", json=payload(studied_on="2026-10-09")).json()
    assert created["studied_on"] == "2026-10-09"


def test_skipped_block_rejects_session_and_completed_block_cannot_move(client):
    skipped, done = friday_blocks(client)[0], friday_blocks(client)[2]
    client.patch(f"/api/v1/occurrences/{skipped['id']}", json={"version": skipped["version"], "status": "skipped"})
    r = client.post("/api/v1/sessions", json=payload(occurrence_id=skipped["id"]))
    assert (r.status_code, r.json()["error"]["code"]) == (422, "occurrence_skipped")
    client.post("/api/v1/sessions", json=payload(occurrence_id=done["id"], complete_occurrence=True))
    current = friday_occurrence(client, done["id"])
    move = client.patch(f"/api/v1/occurrences/{done['id']}", json={"version": current["version"], "planned_on": "2026-10-12"})
    assert (move.status_code, move.json()["error"]["code"]) == (422, "not_pending")


def test_same_id_created_concurrently_returns_original(client, monkeypatch):
    from datetime import date

    from app.db import SessionLocal
    from app.study import service

    body = payload()
    real_check = service._check_topics
    state = {"raced": False}

    def racing(db, topic_ids):
        real_check(db, topic_ids)
        if not state["raced"]:
            state["raced"] = True
            with SessionLocal() as other:  # outro aparelho grava o mesmo id antes deste insert
                service.create_session(other, service.SessionIn(**body), date(2026, 10, 9))
                other.commit()

    monkeypatch.setattr(service, "_check_topics", racing)
    r = client.post("/api/v1/sessions", json=body)
    assert r.status_code == 200
    assert r.json()["id"] == body["id"]
    listed = client.get("/api/v1/sessions", params={"from": "2026-10-09", "to": "2026-10-09"}).json()
    assert listed["total"] == 1
