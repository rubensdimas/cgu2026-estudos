from datetime import date


def test_generate_partial_first_week(client):
    r = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-05"})
    assert r.status_code == 201
    items = r.json()["items"]
    assert [i["slot"]["code"] for i in items] == ["S13", "S14", "S15"]
    again = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-05"})
    assert again.status_code == 200
    assert [i["id"] for i in again.json()["items"]] == [i["id"] for i in items]


def test_full_week_and_invalid_week(client):
    r = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-12"})
    assert r.status_code == 201
    assert len(r.json()["items"]) == 15
    bad = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-13"})
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "invalid_week"


def test_reschedule_skip_and_reopen(client):
    items = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-12"}).json()["items"]
    occ = items[0]
    moved = client.patch(f"/api/v1/occurrences/{occ['id']}",
                         json={"version": occ["version"], "planned_on": "2026-10-13", "window": "after"})
    assert moved.status_code == 200
    assert (moved.json()["planned_on"], moved.json()["window"]) == ("2026-10-13", "after")
    stale = client.patch(f"/api/v1/occurrences/{occ['id']}", json={"version": occ["version"], "status": "skipped"})
    assert stale.status_code == 409
    skipped = client.patch(f"/api/v1/occurrences/{occ['id']}",
                           json={"version": moved.json()["version"], "status": "skipped", "skip_reason": "feriado"})
    assert skipped.json()["status"] == "skipped"
    reopened = client.patch(f"/api/v1/occurrences/{occ['id']}",
                            json={"version": skipped.json()["version"], "status": "pending"})
    assert (reopened.json()["status"], reopened.json()["skip_reason"]) == ("pending", None)


def test_complete_requires_session(client):
    occ = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-05"}).json()["items"][0]
    r = client.patch(f"/api/v1/occurrences/{occ['id']}", json={"version": occ["version"], "status": "completed"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "session_required"


def test_suggested_topic_alternates(client):
    week1 = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-12"}).json()["items"]
    week2 = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-19"}).json()["items"]
    s01 = lambda items: next(i for i in items if i["slot"]["code"] == "S01")["suggested_topic_id"]
    assert (s01(week1), s01(week2)) == ("B01.01", "B02.01")


def test_catalog_and_progress(client):
    subjects = client.get("/api/v1/subjects").json()["items"]
    assert len(subjects) == 13
    assert sum(len(s["topics"]) for s in subjects) == 68
    r = client.put("/api/v1/topics/E01.02/progress", json={"status": "in_progress"})
    assert r.json()["status"] == "in_progress"
    conflict = client.put("/api/v1/topics/E01.02/progress", json={"status": "first_pass", "version": 99})
    assert conflict.status_code == 409


def test_concurrent_week_generation_returns_existing_week(client, monkeypatch):
    from app.planning import service

    first = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-12"}).json()["items"]
    real = service.week_occurrences
    calls = {"n": 0}

    def racing(db, week_start):
        calls["n"] += 1
        return [] if calls["n"] == 1 else real(db, week_start)

    monkeypatch.setattr(service, "week_occurrences", racing)
    r = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-12"})
    assert r.status_code == 200
    assert sorted(i["id"] for i in r.json()["items"]) == sorted(i["id"] for i in first)
