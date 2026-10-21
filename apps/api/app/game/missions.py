"""Missão do dia: abrir o dia, itens, check-out e visão do dia (R13)."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import mission as mission_domain
from app.domain.cycle import week_start_of
from app.errors import ApiError
from app.game.snapshot import ledger, load_world, mission_states
from app.models import DailyMission, MissionItem, Occurrence, ReviewTask
from app.planning.service import current_plan, ensure_week, occurrences_out


def get_mission(db: Session, day: date) -> DailyMission | None:
    return db.scalar(select(DailyMission).where(DailyMission.mission_date == day))


def mission_out(db: Session, mission: DailyMission) -> dict:
    world = load_world(db)
    states = mission_states(world, mission)
    pairs = [(item.required, state) for item, state in states]
    return {
        "id": str(mission.id),
        "date": mission.mission_date,
        "kind": mission.kind,
        "checkout_note": mission.checkout_note,
        "complete": mission_domain.is_complete(pairs),
        "items": [
            {"id": str(item.id), "position": item.position, "kind": item.kind,
             "ref_id": str(item.ref_id) if item.ref_id else None, "required": item.required,
             "target": item.target, "state": state.state, "na_reason": state.reason}
            for item, state in states
        ],
    }


def _plan_day_guard(db: Session, day: date, today: date) -> None:
    plan = current_plan(db)
    if day > today:
        raise ApiError(422, "future_day", "Não é possível abrir um dia futuro.")
    if not plan.starts_on <= day <= plan.ends_on:
        raise ApiError(422, "outside_plan", "Data fora do plano de estudos.")


MAX_WEEKEND_REVIEWS = 4


def due_reviews(db: Session, day: date) -> list[ReviewTask]:
    """Pendentes vencidas até a data, mais antigas primeiro."""
    return list(db.scalars(select(ReviewTask).where(ReviewTask.status == "pending", ReviewTask.due_on <= day)
                           .order_by(ReviewTask.due_on, ReviewTask.created_at)))


def _chosen_reviews(db: Session, day: date, review_ids: list[uuid.UUID]) -> list[ReviewTask]:
    if len(review_ids) > MAX_WEEKEND_REVIEWS:
        raise ApiError(422, "too_many_reviews", "Escolha no máximo 4 revisões na missão livre.")
    due = {r.id: r for r in due_reviews(db, day)}
    for rid in review_ids:
        if rid not in due:
            raise ApiError(422, "invalid_review", "Escolha revisões pendentes já vencidas.", {"review_ids": str(rid)})
    return sorted((due[rid] for rid in set(review_ids)), key=lambda r: (r.due_on, r.created_at))


def open_day(db: Session, day: date, today: date, chosen: list[uuid.UUID],
             review_ids: list[uuid.UUID] = ()) -> tuple[DailyMission, bool]:
    existing = get_mission(db, day)
    if existing is not None:
        return existing, False
    _plan_day_guard(db, day, today)
    kind = mission_domain.mission_kind(day)
    if kind == "weekday":
        ensure_week(db, week_start_of(day))
        occs = list(db.scalars(select(Occurrence).where(Occurrence.planned_on == day)))
        reviews = due_reviews(db, day)[:1]
    else:
        reviews = _chosen_reviews(db, day, list(review_ids))
        if len(chosen) > 2:
            raise ApiError(422, "too_many_blocks", "Escolha no máximo 2 blocos na missão livre.")
        occs = []
        for occ_id in chosen:
            occ = db.get(Occurrence, occ_id)
            if occ is None or occ.status != "pending":
                raise ApiError(422, "invalid_block", "Escolha blocos pendentes.", {"occurrence_ids": str(occ_id)})
            occ.planned_on = day
            occ.version += 1
            occs.append(occ)
    refs = [mission_domain.OccRef(str(o.id), o.status, o.planned_on, o.window) for o in occs]
    question_goal = 0  # F2 passa a usar settings.daily_question_goal
    mission = DailyMission(id=uuid.uuid4(), mission_date=day, kind=kind)
    mission.items = [
        MissionItem(id=uuid.uuid4(), position=i.position, kind=i.kind,
                    ref_id=uuid.UUID(i.ref_id) if i.ref_id else None,
                    target=i.target, required=i.required, na_reason=i.na_reason)
        for i in mission_domain.build_mission(
            day, refs, question_goal, [mission_domain.ReviewRef(str(r.id), r.due_on) for r in reviews])
    ]
    db.add(mission)
    db.flush()
    return mission, True


def set_item_na(db: Session, mission_id: uuid.UUID, item_id: uuid.UUID, reason: str | None) -> DailyMission:
    item = db.get(MissionItem, item_id)
    if item is None or item.mission_id != mission_id:
        raise ApiError(404, "not_found", "Item não encontrado.")
    item.na_reason = (reason or "").strip() or None
    db.flush()
    return db.get(DailyMission, mission_id)


def set_checkout(db: Session, mission_id: uuid.UUID, note: str) -> DailyMission:
    mission = db.get(DailyMission, mission_id)
    if mission is None:
        raise ApiError(404, "not_found", "Missão não encontrada.")
    mission.checkout_note = note.strip() or None
    db.flush()
    return mission


def day_view(db: Session, day: date, today: date) -> dict:
    plan = current_plan(db)
    mission = get_mission(db, day)
    occs = sorted(db.scalars(select(Occurrence).where(Occurrence.planned_on == day)),
                  key=lambda o: o.slot.position)
    week_generated = db.scalar(
        select(Occurrence.id).where(Occurrence.week_start == week_start_of(day)).limit(1)
    ) is not None
    xp_today = sum(e["xp"] for e in ledger(db, today, day, day))
    return {
        "date": day,
        "kind": mission_domain.mission_kind(day),
        "in_plan": plan.starts_on <= day <= plan.ends_on,
        "week_generated": week_generated,
        "occurrences": occurrences_out(db, occs),
        "mission": mission_out(db, mission) if mission else None,
        "xp_today": xp_today,
    }
