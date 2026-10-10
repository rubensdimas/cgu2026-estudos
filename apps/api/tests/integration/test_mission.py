import uuid
from datetime import date


def session_for(client, occurrence_id, minutes=60, studied_on="2026-10-09", **extra):
    body = {"id": str(uuid.uuid4()), "occurrence_id": occurrence_id, "studied_on": studied_on,
            "duration_minutes": minutes, "activity": "theory", "topic_ids": ["C02.01"],
            "complete_occurrence": True}
    body.update(extra)
    return client.post("/api/v1/sessions", json=body)


def test_get_day_does_not_write(client):
    day = client.get("/api/v1/days/2026-10-09").json()
    assert (day["week_generated"], day["mission"], day["occurrences"]) == (False, None, [])


def test_open_day_generates_week_and_is_idempotent(client):
    r = client.post("/api/v1/days/2026-10-09/mission", json={})
    assert r.status_code == 201
    kinds = [(i["kind"], i["required"]) for i in r.json()["items"]]
    assert kinds == [("block", True), ("block", True), ("block", True), ("checkout", False)]
    again = client.post("/api/v1/days/2026-10-09/mission", json={})
    assert again.status_code == 200
    assert again.json()["id"] == r.json()["id"]


def test_future_and_out_of_plan_days_rejected(client):
    assert client.post("/api/v1/days/2026-10-10/mission", json={}).status_code == 422
    assert client.post("/api/v1/days/2026-10-08/mission", json={}).status_code == 422


def test_block_registered_before_opening_day_still_counts(client):
    occ = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-05"}).json()["items"][0]
    session_for(client, occ["id"])
    mission = client.post("/api/v1/days/2026-10-09/mission", json={}).json()
    first = mission["items"][0]
    assert (first["ref_id"], first["state"]) == (occ["id"], "done")


def test_mission_completion_with_not_applicable_and_bonus(client):
    mission = client.post("/api/v1/days/2026-10-09/mission", json={}).json()
    blocks = [i for i in mission["items"] if i["kind"] == "block"]
    for item in blocks[1:]:
        r = client.patch(f"/api/v1/missions/{mission['id']}/items/{item['id']}", json={"na_reason": "indisponível"})
        assert r.json()["complete"] is False
    done = session_for(client, blocks[0]["ref_id"])
    delta = done.json()["game_delta"]
    assert delta["mission_complete"] == ["2026-10-09"]
    assert delta["xp_gained"] == 60 + 20 + 50
    checkout = client.put(f"/api/v1/missions/{mission['id']}/checkout", json={"note": "Prazos da LAI."})
    assert checkout.json()["game_delta"]["xp_gained"] == 10


def test_all_not_applicable_is_not_complete(client):
    mission = client.post("/api/v1/days/2026-10-09/mission", json={}).json()
    for item in mission["items"]:
        if item["required"]:
            last = client.patch(f"/api/v1/missions/{mission['id']}/items/{item['id']}", json={"na_reason": "x"})
    assert last.json()["complete"] is False


def test_rescheduled_block_becomes_not_applicable(client):
    mission = client.post("/api/v1/days/2026-10-09/mission", json={}).json()
    day = client.get("/api/v1/days/2026-10-09").json()
    occ = day["occurrences"][0]
    client.patch(f"/api/v1/occurrences/{occ['id']}", json={"version": occ["version"], "planned_on": "2026-10-12"})
    items = client.get("/api/v1/days/2026-10-09").json()["mission"]["items"]
    moved = next(i for i in items if i["ref_id"] == occ["id"])
    assert (moved["state"], moved["na_reason"]) == ("not_applicable", "rescheduled")


def test_free_mission_on_weekend(client, clock):
    pending = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-05"}).json()["items"]
    clock.today = date(2026, 10, 10)
    too_many = client.post("/api/v1/days/2026-10-10/mission",
                           json={"occurrence_ids": [o["id"] for o in pending]})
    assert too_many.status_code == 422
    r = client.post("/api/v1/days/2026-10-10/mission", json={"occurrence_ids": [pending[0]["id"]]})
    assert r.status_code == 201
    assert r.json()["kind"] == "free"
    day = client.get("/api/v1/days/2026-10-10").json()
    assert [o["id"] for o in day["occurrences"]] == [pending[0]["id"]]


def test_concurrent_open_day_returns_existing_mission(client, monkeypatch):
    from app.game import missions

    first = client.post("/api/v1/days/2026-10-09/mission", json={}).json()
    real = missions.get_mission
    calls = {"n": 0}

    def racing(db, day):
        calls["n"] += 1
        return None if calls["n"] == 1 else real(db, day)

    monkeypatch.setattr(missions, "get_mission", racing)
    r = client.post("/api/v1/days/2026-10-09/mission", json={})
    assert r.status_code == 200
    assert r.json()["id"] == first["id"]


def test_moving_session_date_uncompletes_original_mission(client, clock):
    clock.today = date(2026, 10, 12)
    mission = client.post("/api/v1/days/2026-10-09/mission", json={}).json()
    blocks = [i for i in mission["items"] if i["kind"] == "block"]
    for item in blocks[1:]:
        client.patch(f"/api/v1/missions/{mission['id']}/items/{item['id']}", json={"na_reason": "x"})
    created = session_for(client, blocks[0]["ref_id"]).json()
    assert created["game_delta"]["mission_complete"] == ["2026-10-09"]
    moved = client.patch(f"/api/v1/sessions/{created['id']}",
                         json={"version": created["version"], "studied_on": "2026-10-12"})
    assert moved.json()["game_delta"]["xp_gained"] == -50
    assert client.get("/api/v1/days/2026-10-09").json()["mission"]["complete"] is False
