"""Missão do dia ([10] §2, R13)."""

from dataclasses import dataclass, field
from datetime import date

WINDOW_ORDER = {"before": 0, "middle": 1, "after": 2}


@dataclass(frozen=True)
class OccRef:
    id: str
    status: str
    planned_on: date
    window: str


@dataclass(frozen=True)
class MissionItemInput:
    position: int
    kind: str  # block | review | questions | checkout
    required: bool
    ref_id: str | None = None
    target: int | None = None
    na_reason: str | None = None


@dataclass(frozen=True)
class DayFacts:
    mission_date: date
    occurrence_status: dict[str, str] = field(default_factory=dict)
    occurrence_planned_on: dict[str, date] = field(default_factory=dict)
    occurrence_completed_on: dict[str, date] = field(default_factory=dict)
    question_items: int = 0
    checkout_saved: bool = False


@dataclass(frozen=True)
class ItemState:
    state: str  # pending | done | not_applicable
    reason: str | None = None


def mission_kind(day: date) -> str:
    return "free" if day.weekday() >= 5 else "weekday"


def build_mission(day: date, occurrences: list[OccRef], question_goal: int = 0) -> list[MissionItemInput]:
    items: list[MissionItemInput] = []
    for occ in sorted(occurrences, key=lambda o: WINDOW_ORDER[o.window]):
        items.append(MissionItemInput(len(items), "block", True, ref_id=occ.id))
    if question_goal > 0:
        items.append(MissionItemInput(len(items), "questions", False, target=question_goal))
    items.append(MissionItemInput(len(items), "checkout", False))
    return items


def item_state(item: MissionItemInput, facts: DayFacts) -> ItemState:
    if item.kind == "block":
        # Estudo real vence a marcação manual de "não se aplica".
        completed_on = facts.occurrence_completed_on.get(item.ref_id)
        if completed_on is not None and completed_on <= facts.mission_date:
            return ItemState("done")
    if item.na_reason:
        return ItemState("not_applicable", item.na_reason)
    if item.kind == "block":
        if facts.occurrence_status.get(item.ref_id) == "skipped":
            return ItemState("not_applicable", "skipped")
        if facts.occurrence_planned_on.get(item.ref_id) != facts.mission_date:
            return ItemState("not_applicable", "rescheduled")
        return ItemState("pending")
    if item.kind == "questions":
        return ItemState("done" if facts.question_items >= (item.target or 0) else "pending")
    if item.kind == "checkout":
        return ItemState("done" if facts.checkout_saved else "pending")
    return ItemState("pending")


def is_complete(states: list[tuple[bool, ItemState]]) -> bool:
    required = [s.state for req, s in states if req]
    return (
        bool(required)
        and all(s in ("done", "not_applicable") for s in required)
        and any(s == "done" for s in required)
    )


def optional_done(states: list[tuple[bool, ItemState]]) -> int:
    return sum(1 for req, s in states if not req and s.state == "done")
