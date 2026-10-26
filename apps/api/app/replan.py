"""Replanejamento único para 1 tópico por dia (plano de 26/10/2026). Idempotente.

Uso: `python -m app.replan`, depois de um backup e com o seed já tendo carregado o template de 26/10.
"""

import json
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import SessionLocal
from app.domain.reviews import OFFSETS
from app.models import AppSettings, CycleTemplate, Occurrence, ReviewTask, StudySession
from app.planning.service import current_plan, ensure_week, week_occurrences

CUTOVER = date(2026, 10, 26)
SKIP_REASON = "replanejamento: 1 tópico/dia"
TOPICS_PER_WEEKEND_DAY = 3
# A cadeia nova parte da âncora (fim de semana): 1ª revisão nela, as demais 7 e 21 dias depois.
ANCHOR_SHIFT = {1: 0, 7: 7, 21: 21}
WEEKLY_GOALS = {"minutes": 300, "blocks": 5, "questions": {"P1": 15, "P2": 15, "P3": 30},
                "essays": {"per_week": 1}, "missions": 5}
DAILY_QUESTION_GOAL = 10


def weekend_days(start: date):
    day = start
    while True:
        if day.weekday() >= 5:
            yield day
        day += timedelta(days=1)


def _check_week(db: Session) -> None:
    plan = current_plan(db)
    template = db.scalar(select(CycleTemplate).where(
        CycleTemplate.study_plan_id == plan.id, CycleTemplate.effective_from == CUTOVER))
    if template is None:
        raise RuntimeError("Template de 26/10 não encontrado: rode `python -m app.seed` antes.")
    if any(o.slot.cycle_template_id != template.id for o in week_occurrences(db, CUTOVER)):
        raise RuntimeError("A semana de 26/10 já foi gerada com o ciclo antigo; ajuste-a manualmente antes.")


def _skip_last_week(db: Session) -> int:
    rows = db.scalars(select(Occurrence).where(
        Occurrence.week_start == CUTOVER - timedelta(days=7), Occurrence.status == "pending"))
    count = 0
    for occ in rows:
        occ.status, occ.skip_reason = "skipped", SKIP_REASON
        occ.version += 1
        count += 1
    return count


def _latest_theory_sessions(db: Session) -> dict[str, StudySession]:
    sessions = db.scalars(select(StudySession).where(
        StudySession.deleted_at.is_(None), StudySession.activity == "theory", StudySession.studied_on < CUTOVER,
    ).order_by(StudySession.studied_on, StudySession.created_at))
    latest: dict[str, StudySession] = {}
    for s in sessions:
        for topic_id in s.topic_ids:
            latest[topic_id] = s
    return latest


def _reschedule_reviews(db: Session, exam_on: date) -> dict[str, int]:
    counts = {"reviews_rescheduled": 0, "reviews_created": 0, "reviews_dismissed": 0}
    latest = _latest_theory_sessions(db)
    by_topic: dict[str, list[ReviewTask]] = {}
    for r in db.scalars(select(ReviewTask).where(ReviewTask.topic_id.in_(list(latest)))):
        by_topic.setdefault(r.topic_id, []).append(r)
    for topic_id, reviews in by_topic.items():
        for r in reviews:
            if r.session_id != latest[topic_id].id and r.status == "pending":
                r.status = "dismissed"
                r.version += 1
                counts["reviews_dismissed"] += 1

    def open_offsets(topic_id: str) -> list[int]:
        own = {r.offset_days: r for r in by_topic.get(topic_id, []) if r.session_id == latest[topic_id].id}
        return [o for o in OFFSETS if o not in own or own[o].status == "pending"]

    order = sorted((t for t in latest if open_offsets(t)), key=lambda t: (latest[t].studied_on, t))
    anchors = weekend_days(CUTOVER)
    anchor = None
    for i, topic_id in enumerate(order):
        if i % TOPICS_PER_WEEKEND_DAY == 0:
            anchor = next(anchors)
        session = latest[topic_id]
        own = {r.offset_days: r for r in by_topic.get(topic_id, []) if r.session_id == session.id}
        for offset in open_offsets(topic_id):
            due_on = anchor + timedelta(days=ANCHOR_SHIFT[offset])
            if due_on >= exam_on:
                continue
            review = own.get(offset)
            if review is None:
                db.add(ReviewTask(session_id=session.id, topic_id=topic_id, offset_days=offset, due_on=due_on))
                counts["reviews_created"] += 1
            elif review.due_on != due_on:
                review.due_on = due_on
                review.version += 1
                counts["reviews_rescheduled"] += 1
    return counts


def replan(db: Session, today: date) -> dict:
    _check_week(db)
    result = {"blocks_skipped": _skip_last_week(db)}
    result.update(_reschedule_reviews(db, current_plan(db).exam_version.exam_date))
    settings = db.get(AppSettings, 1)
    settings.weekly_goals, settings.daily_question_goal = WEEKLY_GOALS, DAILY_QUESTION_GOAL
    db.flush()
    _, created = ensure_week(db, CUTOVER)
    result["week_generated"] = created
    return result


def main() -> None:
    with SessionLocal() as db:
        result = replan(db, get_today())
        db.commit()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
