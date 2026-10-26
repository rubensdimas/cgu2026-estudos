"""Snapshot do jogo: monta fatos a partir do banco e chama as funções puras (R14)."""

import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import mission as mission_domain
from app.domain.cycle import CycleError, select_template, week_start_of
from app.domain.streak import StreakState, streak_state
from app.domain.weeks import is_week_complete, minutes_goal_for_week
from app.domain.reviews import review_xp
from app.domain.xp import (
    BlockFact, GameFacts, LevelInfo, MissionFact, ReviewFact, SessionFact, XpEntry, level_for_xp, xp_ledger,
)
from app.game import config as game_config
from app.models import AppSettings, DailyMission, DayOff, MissionItem, Occurrence, ReviewTask, StudySession
from app.planning.service import current_plan, templates, to_input

T = TypeVar("T")


@dataclass
class Snapshot:
    ledger: list[XpEntry]
    total: int
    level: LevelInfo
    streak: StreakState
    mission_complete: dict[date, bool]


@dataclass
class World:
    """Registros ativos carregados uma vez por cálculo."""
    occurrences: dict[uuid.UUID, Occurrence]
    completed_on: dict[uuid.UUID, date]
    minutes_by_date: dict[date, int]
    sessions: list[SessionFact]
    reviews: dict[uuid.UUID, ReviewTask]


def load_world(db: Session) -> World:
    occurrences = {o.id: o for o in db.scalars(select(Occurrence))}
    rows = db.execute(
        select(StudySession.id, StudySession.occurrence_id, StudySession.studied_on, StudySession.duration_minutes)
        .where(StudySession.deleted_at.is_(None))
    ).all()
    completed_on: dict[uuid.UUID, date] = {}
    minutes_by_date: dict[date, int] = defaultdict(int)
    for _, occ_id, studied_on, minutes in rows:
        minutes_by_date[studied_on] += minutes
        if occ_id is not None and occurrences[occ_id].status == "completed":
            completed_on[occ_id] = max(completed_on.get(occ_id, studied_on), studied_on)
    sessions = [SessionFact(str(sid), studied_on, minutes) for sid, _, studied_on, minutes in rows]
    reviews = {r.id: r for r in db.scalars(select(ReviewTask))}
    return World(occurrences, completed_on, dict(minutes_by_date), sessions, reviews)


def day_facts(world: World, mission: DailyMission) -> mission_domain.DayFacts:
    refs = [i.ref_id for i in mission.items if i.kind == "block" and i.ref_id is not None]
    review_refs = [i.ref_id for i in mission.items if i.kind == "review" and i.ref_id is not None]
    return mission_domain.DayFacts(
        mission_date=mission.mission_date,
        occurrence_status={str(r): world.occurrences[r].status for r in refs},
        occurrence_planned_on={str(r): world.occurrences[r].planned_on for r in refs},
        occurrence_completed_on={str(r): world.completed_on[r] for r in refs if r in world.completed_on},
        question_items=0,
        checkout_saved=bool(mission.checkout_note and mission.checkout_note.strip()),
        review_status={str(r): world.reviews[r].status for r in review_refs if r in world.reviews},
        review_completed_on={str(r): world.reviews[r].completed_on for r in review_refs
                             if r in world.reviews and world.reviews[r].completed_on},
    )


def item_input(item: MissionItem) -> mission_domain.MissionItemInput:
    return mission_domain.MissionItemInput(
        item.position, item.kind, item.required, str(item.ref_id) if item.ref_id else None, item.target, item.na_reason
    )


def mission_states(world: World, mission: DailyMission) -> list[tuple[MissionItem, mission_domain.ItemState]]:
    facts = day_facts(world, mission)
    return [(item, mission_domain.item_state(item_input(item), facts)) for item in mission.items]


def complete_weeks(db: Session, world: World) -> frozenset[date]:
    settings = db.get(AppSettings, 1)
    plan = current_plan(db)
    by_week: dict[date, list[Occurrence]] = defaultdict(list)
    for occ in world.occurrences.values():
        by_week[occ.week_start].append(occ)
    # Semanas sem ocorrências geradas também completam pelos minutos (docs/10 §3).
    for day in world.minutes_by_date:
        if plan.starts_on <= day <= plan.ends_on:
            by_week.setdefault(week_start_of(day), [])
    template_inputs = [(to_input(t), t.weekly_minutes) for t in templates(db, plan)]

    def weekly_minutes(ws: date) -> int:
        """Meta do template vigente na semana: mudar o ciclo não reescreve semanas passadas."""
        try:
            chosen = select_template([t for t, _ in template_inputs], ws)
        except CycleError:
            return settings.weekly_goals["minutes"]
        return next(m for t, m in template_inputs if t.effective_from == chosen.effective_from)

    done = set()
    for ws, occs in by_week.items():
        minutes = sum(world.minutes_by_date.get(ws + timedelta(days=i), 0) for i in range(7))
        goal = minutes_goal_for_week(ws, plan.starts_on, sum(o.slot.minutes for o in occs), weekly_minutes(ws))
        if is_week_complete([o.status for o in occs], minutes, goal):
            done.add(ws)
    return frozenset(done)


def review_facts(db: Session) -> tuple[ReviewFact, ...]:
    """Só a revisão concluída explicitamente pontua; as atrasadas fechadas junto (`closed_by`) não."""
    rows = db.execute(select(ReviewTask.id, ReviewTask.due_on, ReviewTask.completed_on).where(
        ReviewTask.status == "completed", ReviewTask.closed_by.is_(None)))
    return tuple(ReviewFact(str(rid), done, review_xp(due, done)) for rid, due, done in rows)


def build_snapshot(db: Session, today: date) -> Snapshot:
    settings = db.get(AppSettings, 1)
    plan = current_plan(db)
    world = load_world(db)
    missions = list(db.scalars(select(DailyMission)))
    mission_facts, mission_complete = [], {}
    for m in missions:
        pairs = [(item.required, state) for item, state in mission_states(world, m)]
        complete = mission_domain.is_complete(pairs)
        mission_complete[m.mission_date] = complete
        mission_facts.append(MissionFact(str(m.id), m.mission_date, complete, mission_domain.optional_done(pairs)))
    weeks = complete_weeks(db, world)
    facts = GameFacts(
        sessions=tuple(world.sessions),
        blocks=tuple(BlockFact(str(oid), d) for oid, d in world.completed_on.items()),
        missions=tuple(mission_facts),
        complete_week_starts=weeks,
        reviews=review_facts(db),
    )
    ledger = xp_ledger(facts, game_config.xp_table(settings.streak_min_minutes))
    total = sum(e.xp for e in ledger)
    day_offs = set(db.scalars(select(DayOff.day)))
    streak = streak_state(world.minutes_by_date, day_offs, set(weeks), plan.starts_on, today,
                          settings.streak_min_minutes, settings.max_freezes)
    return Snapshot(ledger, total, level_for_xp(total, game_config.titles()), streak, mission_complete)


def game_delta(before: Snapshot, after: Snapshot) -> dict:
    old = {(e.source, e.ref_id, e.date): e.xp for e in before.ledger}
    new = {(e.source, e.ref_id, e.date): e.xp for e in after.ledger}
    entries = [
        {"source": k[0], "ref_id": k[1], "date": k[2], "xp": new.get(k, 0) - old.get(k, 0)}
        for k in sorted(set(old) | set(new), key=lambda k: (k[2], k[0], k[1]))
        if new.get(k, 0) != old.get(k, 0)
    ]
    return {
        "xp_gained": after.total - before.total,
        "entries": entries,
        "level_up": after.level.level if after.level.level > before.level.level else None,
        "level_title": after.level.title if after.level.level > before.level.level else None,
        "mission_complete": sorted(
            d for d, c in after.mission_complete.items() if c and not before.mission_complete.get(d)
        ),
        "streak": after.streak.current,
    }


def tracked(db: Session, today: date, action: Callable[[], T]) -> tuple[T, dict]:
    """Executa uma mutação em transação e devolve o efeito no jogo."""
    before = build_snapshot(db, today)
    result = action()
    db.flush()
    after = build_snapshot(db, today)
    db.commit()
    return result, game_delta(before, after)


def calendar(db: Session, today: date, start: date, end: date) -> dict:
    """Dias ativos (≥ mínimo), congelados e neutros (fim de semana ou folga) no intervalo."""
    settings = db.get(AppSettings, 1)
    plan = current_plan(db)
    world = load_world(db)
    day_offs = set(db.scalars(select(DayOff.day)))
    streak = streak_state(world.minutes_by_date, day_offs, set(complete_weeks(db, world)), plan.starts_on, today,
                          settings.streak_min_minutes, settings.max_freezes)
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]

    def counts(d: date) -> bool:  # dia que entra na sequência (docs/10 §5)
        return plan.starts_on <= d <= plan.ends_on and d.weekday() < 5 and d not in day_offs

    active = [d for d in days if counts(d) and world.minutes_by_date.get(d, 0) >= settings.streak_min_minutes]
    neutral = [d for d in days if not counts(d)]
    return {
        "active_days": active,
        "frozen_days": [d for d in streak.frozen_days if start <= d <= end],
        "neutral_days": neutral,
    }


def summary(db: Session, today: date) -> dict:
    snap = build_snapshot(db, today)
    plan = current_plan(db)
    settings = db.get(AppSettings, 1)
    exam_date = plan.exam_version.exam_date
    marked = set(db.scalars(select(DayOff.day)))
    upcoming = [h for h in game_config.holiday_suggestions()
                if date.fromisoformat(h["date"]) in (today, today + timedelta(days=1))
                and date.fromisoformat(h["date"]) not in marked]
    return {
        "today": today,
        "exam_date": exam_date,
        "days_to_exam": (exam_date - today).days,
        "xp_total": snap.total,
        "level": snap.level.level,
        "title": snap.level.title,
        "xp_into_level": snap.level.xp_into_level,
        "xp_for_next": snap.level.xp_for_next,
        "streak": {
            "current": snap.streak.current,
            "best": snap.streak.best,
            "freezes_available": snap.streak.freezes_available,
            "frozen_days": list(snap.streak.frozen_days),
            "at_stake_today": snap.streak.at_stake_today,
            "minutes_today": snap.streak.minutes_today,
            "min_minutes": settings.streak_min_minutes,
        },
        "holiday_suggestion": upcoming[0] if upcoming else None,
    }


def ledger(db: Session, today: date, start: date, end: date) -> list[dict]:
    snap = build_snapshot(db, today)
    return [{"date": e.date, "source": e.source, "ref_id": e.ref_id, "xp": e.xp}
            for e in snap.ledger if start <= e.date <= end]
