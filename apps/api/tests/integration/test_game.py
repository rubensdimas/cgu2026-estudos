import uuid
from datetime import date, timedelta


def study(client, day: date, minutes: int):
    body = {"id": str(uuid.uuid4()), "studied_on": day.isoformat(), "duration_minutes": minutes,
            "activity": "theory", "topic_ids": ["E01.02"]}
    assert client.post("/api/v1/sessions", json=body).status_code == 201


def test_summary_empty_state(client):
    s = client.get("/api/v1/game/summary").json()
    assert (s["xp_total"], s["level"], s["title"], s["days_to_exam"]) == (0, 1, "Estagiário", 65)
    assert s["streak"]["current"] == 0
    assert s["streak"]["at_stake_today"] is True


def test_streak_with_day_off_and_break(client, clock):
    study(client, date(2026, 10, 9), 45)
    clock.today = date(2026, 10, 14)
    study(client, date(2026, 10, 12), 30)
    assert client.get("/api/v1/game/summary").json()["streak"]["current"] == 0
    r = client.put("/api/v1/day-offs/2026-10-13", json={"reason": "compromisso"})
    assert r.status_code == 200
    s = client.get("/api/v1/game/summary").json()["streak"]
    assert (s["current"], s["best"]) == (2, 2)
    assert client.delete("/api/v1/day-offs/2026-10-13").status_code == 204
    assert client.get("/api/v1/game/summary").json()["streak"]["current"] == 0


def test_weekend_day_off_rejected(client):
    assert client.put("/api/v1/day-offs/2026-10-10", json={"reason": "x"}).status_code == 422


def test_holiday_suggestion_on_eve(client, clock):
    clock.today = date(2026, 10, 11)
    assert client.get("/api/v1/game/summary").json()["holiday_suggestion"]["date"] == "2026-10-12"
    client.put("/api/v1/day-offs/2026-10-12", json={"reason": "Nossa Senhora Aparecida"})
    assert client.get("/api/v1/game/summary").json()["holiday_suggestion"] is None


def test_full_week_completion_grants_xp_and_freeze(client, clock):
    clock.today = date(2026, 10, 20)
    client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-12"})
    for i in range(5):
        study(client, date(2026, 10, 12) + timedelta(days=i), 180)
    s = client.get("/api/v1/game/summary").json()
    assert s["streak"]["current"] == 5
    assert s["streak"]["frozen_days"] == ["2026-10-19"]
    ledger = client.get("/api/v1/game/xp", params={"from": "2026-10-18", "to": "2026-10-18"}).json()["items"]
    assert [(e["source"], e["xp"]) for e in ledger] == [("week_complete", 150)]


def test_level_up_reported(client, clock):
    clock.today = date(2026, 10, 12)
    study(client, date(2026, 10, 9), 60)
    body = {"id": str(uuid.uuid4()), "studied_on": "2026-10-12", "duration_minutes": 60,
            "activity": "theory", "topic_ids": ["E01.02"]}
    delta = client.post("/api/v1/sessions", json=body).json()["game_delta"]
    assert delta["level_up"] == 2
    assert delta["level_title"] == "Estagiário"


def test_deleting_session_removes_its_xp(client):
    body = {"id": str(uuid.uuid4()), "studied_on": "2026-10-09", "duration_minutes": 40,
            "activity": "theory", "topic_ids": ["E01.02"]}
    client.post("/api/v1/sessions", json=body)
    assert client.get("/api/v1/game/summary").json()["xp_total"] == 40
    assert client.delete(f"/api/v1/sessions/{body['id']}").status_code == 204
    assert client.get("/api/v1/game/summary").json()["xp_total"] == 0


def test_week_completed_by_minutes_without_generated_occurrences(client, clock):
    clock.today = date(2026, 10, 20)
    for i in range(5):
        study(client, date(2026, 10, 12) + timedelta(days=i), 180)
    s = client.get("/api/v1/game/summary").json()["streak"]
    assert (s["current"], s["frozen_days"]) == (5, ["2026-10-19"])
    ledger = client.get("/api/v1/game/xp", params={"from": "2026-10-18", "to": "2026-10-18"}).json()["items"]
    assert [(e["source"], e["xp"]) for e in ledger] == [("week_complete", 150)]


def test_calendar_marks_active_frozen_and_neutral_days(client, clock):
    clock.today = date(2026, 10, 21)
    study(client, date(2026, 10, 9), 45)
    for i in range(5):
        study(client, date(2026, 10, 12) + timedelta(days=i), 180)
    client.put("/api/v1/day-offs/2026-10-20", json={"reason": "consulta"})
    cal = client.get("/api/v1/game/calendar", params={"from": "2026-10-09", "to": "2026-10-21"}).json()
    assert cal["active_days"] == ["2026-10-09", "2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16"]
    assert cal["frozen_days"] == ["2026-10-19"]
    assert cal["neutral_days"] == ["2026-10-10", "2026-10-11", "2026-10-17", "2026-10-18", "2026-10-20"]


def test_calendar_rejects_invalid_range(client):
    assert client.get("/api/v1/game/calendar", params={"from": "2026-10-20", "to": "2026-10-09"}).status_code == 422
    assert client.get("/api/v1/game/calendar", params={"from": "2026-01-01", "to": "2027-03-01"}).status_code == 422


def test_config_exposes_level_titles(client):
    levels = client.get("/api/v1/game/config").json()["levels"]
    assert [l["title"] for l in levels] == ["Estagiário", "Analista", "Auditor Júnior", "Auditor", "AFFC"]
    assert levels[-1] == {"from": 18, "to": None, "title": "AFFC"}


def test_calendar_treats_pre_plan_days_and_weekend_study_as_neutral(client, clock):
    clock.today = date(2026, 10, 12)
    study(client, date(2026, 10, 9), 45)
    study(client, date(2026, 10, 10), 60)
    cal = client.get("/api/v1/game/calendar", params={"from": "2026-10-05", "to": "2026-10-12"}).json()
    assert cal["active_days"] == ["2026-10-09"]
    assert cal["neutral_days"] == ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-10", "2026-10-11"]
