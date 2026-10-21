import uuid
from datetime import date, datetime, timezone

from app.catalog.progress import promote, promote_for_session, promote_from_history
from app.models import SessionTopic, StudySession, TopicProgress


def loose_session(db, topic_ids, studied_on=date(2026, 10, 9), activity="theory", deleted=False):
    session = StudySession(
        id=uuid.uuid4(), studied_on=studied_on, duration_minutes=50, activity=activity, notes="",
        deleted_at=datetime.now(timezone.utc) if deleted else None,
        topic_links=[SessionTopic(topic_id=t) for t in topic_ids],
    )
    db.add(session)
    db.flush()
    return session


def state(db, topic_id):
    row = db.get(TopicProgress, topic_id)
    return row and (row.status, row.declared_on, row.version)


def test_promote_creates_and_raises_but_never_lowers(db):
    d1, d2, d3 = date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7)
    promote(db, ["C02.01"], "in_progress", d1)
    assert state(db, "C02.01") == ("in_progress", d1, 1)
    promote(db, ["C02.01"], "first_pass", d2)
    assert state(db, "C02.01") == ("first_pass", d2, 2)
    promote(db, ["C02.01"], "in_progress", d3)
    assert state(db, "C02.01") == ("first_pass", d2, 2)


def test_promote_keeps_reviewed_topic_in_multi_topic_call(db):
    db.add(TopicProgress(topic_id="C04.01", status="reviewed", declared_on=date(2026, 10, 1)))
    db.flush()
    promote(db, ["C02.01", "C04.01"], "first_pass", date(2026, 10, 9))
    assert state(db, "C02.01") == ("first_pass", date(2026, 10, 9), 1)
    assert state(db, "C04.01") == ("reviewed", date(2026, 10, 1), 1)


def test_promote_for_session_ignores_non_theory_and_deleted(db):
    promote_for_session(db, loose_session(db, ["C02.01"], activity="questions"))
    promote_for_session(db, loose_session(db, ["C03.01"], deleted=True))
    assert state(db, "C02.01") is None
    assert state(db, "C03.01") is None


def test_promote_from_history_uses_earliest_qualifying_session(db):
    loose_session(db, ["C02.01"], studied_on=date(2026, 10, 8))
    loose_session(db, ["C02.01"], studied_on=date(2026, 10, 5))
    promote_from_history(db)
    assert state(db, "C02.01") == ("first_pass", date(2026, 10, 5), 1)
    promote_from_history(db)
    assert state(db, "C02.01") == ("first_pass", date(2026, 10, 5), 1)



def test_promote_from_history_keeps_existing_first_pass_untouched(db):
    db.add(TopicProgress(topic_id="C04.01", status="first_pass", declared_on=date(2026, 10, 1)))
    loose_session(db, ["C04.01"])
    promote_from_history(db)
    assert state(db, "C04.01") == ("first_pass", date(2026, 10, 1), 1)

def friday_block(client):
    return client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-05"}).json()["items"][0]


def post_session(client, topic_ids, **over):
    body = {"id": str(uuid.uuid4()), "studied_on": "2026-10-09", "duration_minutes": 50,
            "activity": "theory", "topic_ids": topic_ids, "notes": ""}
    body.update(over)
    r = client.post("/api/v1/sessions", json=body)
    assert r.status_code in (200, 201), r.text
    return r.json()


def progress(client, topic_id):
    subjects = client.get("/api/v1/subjects").json()["items"]
    return next(t["progress"] for s in subjects for t in s["topics"] if t["id"] == topic_id)


def complete_block(client, occ_id):
    items = client.get("/api/v1/occurrences", params={"from": "2026-10-09", "to": "2026-10-09"}).json()["items"]
    occ = next(o for o in items if o["id"] == occ_id)
    r = client.patch(f"/api/v1/occurrences/{occ_id}", json={"version": occ["version"], "status": "completed"})
    assert r.status_code == 200, r.text


def test_loose_theory_session_marks_first_pass(client):
    post_session(client, ["C02.01"])
    assert progress(client, "C02.01") == {"status": "first_pass", "declared_on": "2026-10-09", "version": 1}


def test_questions_session_does_not_change_progress(client):
    post_session(client, ["C02.01"], activity="questions")
    assert progress(client, "C02.01") is None


def test_theory_in_pending_block_marks_in_progress_then_completion_promotes(client):
    occ = friday_block(client)
    post_session(client, ["C02.01"], occurrence_id=occ["id"], complete_occurrence=False)
    assert progress(client, "C02.01")["status"] == "in_progress"
    complete_block(client, occ["id"])
    assert progress(client, "C02.01")["status"] == "first_pass"


def test_second_session_completing_block_promotes_first_session_topics(client):
    occ = friday_block(client)
    post_session(client, ["C02.01"], occurrence_id=occ["id"], complete_occurrence=False)
    post_session(client, ["C03.01"], occurrence_id=occ["id"], complete_occurrence=True)
    assert progress(client, "C02.01")["status"] == "first_pass"
    assert progress(client, "C03.01")["status"] == "first_pass"


def test_resend_same_session_does_not_bump_version(client):
    body = {"id": str(uuid.uuid4())}
    post_session(client, ["C02.01"], **body)
    post_session(client, ["C02.01"], **body)
    assert progress(client, "C02.01")["version"] == 1


def test_editing_topics_promotes_only_new_ones_and_never_reverts(client):
    session = post_session(client, ["C02.01"])
    r = client.patch(f"/api/v1/sessions/{session['id']}", json={"version": session["version"], "topic_ids": ["C03.01"]})
    assert r.status_code == 200, r.text
    assert progress(client, "C03.01")["status"] == "first_pass"
    assert client.delete(f"/api/v1/sessions/{session['id']}").status_code == 204
    assert progress(client, "C02.01")["status"] == "first_pass"
    assert progress(client, "C03.01")["status"] == "first_pass"


def test_deleted_session_does_not_promote_on_block_completion(client):
    occ = friday_block(client)
    a = post_session(client, ["C02.01"], occurrence_id=occ["id"], complete_occurrence=False)
    post_session(client, ["C03.01"], occurrence_id=occ["id"], complete_occurrence=False)
    assert client.delete(f"/api/v1/sessions/{a['id']}").status_code == 204
    complete_block(client, occ["id"])
    assert progress(client, "C02.01")["status"] == "in_progress"
    assert progress(client, "C03.01")["status"] == "first_pass"
