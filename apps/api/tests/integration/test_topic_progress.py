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
