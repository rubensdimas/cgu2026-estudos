"""Extrato de XP e nível ([10] §3–4). Tudo derivado dos registros."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass(frozen=True)
class XpTable:
    per_session_minute: int = 1
    session_minutes_daily_cap: int = 240
    block_completed: int = 20
    mission_complete: int = 50
    mission_optional_item: int = 10
    week_complete: int = 150
    weekend_active_day: int = 20
    weekend_min_minutes: int = 30


@dataclass(frozen=True)
class SessionFact:
    id: str
    studied_on: date
    minutes: int


@dataclass(frozen=True)
class BlockFact:
    occurrence_id: str
    completed_on: date


@dataclass(frozen=True)
class MissionFact:
    mission_id: str
    mission_date: date
    complete: bool
    optional_done: int


@dataclass(frozen=True)
class GameFacts:
    sessions: tuple[SessionFact, ...] = ()
    blocks: tuple[BlockFact, ...] = ()
    missions: tuple[MissionFact, ...] = ()
    complete_week_starts: frozenset[date] = field(default_factory=frozenset)


@dataclass(frozen=True)
class XpEntry:
    date: date
    source: str
    ref_id: str
    xp: int


@dataclass(frozen=True)
class TitleBand:
    first: int
    last: int | None
    title: str


@dataclass(frozen=True)
class LevelInfo:
    level: int
    title: str
    xp_total: int
    xp_into_level: int
    xp_for_next: int


DEFAULT_TITLES = (
    TitleBand(1, 3, "Estagiário"),
    TitleBand(4, 7, "Analista"),
    TitleBand(8, 12, "Auditor Júnior"),
    TitleBand(13, 17, "Auditor"),
    TitleBand(18, None, "AFFC"),
)


def xp_ledger(facts: GameFacts, table: XpTable) -> list[XpEntry]:
    entries: list[XpEntry] = []
    by_day: dict[date, list[SessionFact]] = defaultdict(list)
    for s in facts.sessions:
        by_day[s.studied_on].append(s)
    for day in sorted(by_day):
        remaining = table.session_minutes_daily_cap
        day_sessions = sorted(by_day[day], key=lambda s: s.id)
        for s in day_sessions:
            xp = min(s.minutes * table.per_session_minute, remaining)
            remaining -= xp
            if xp > 0:
                entries.append(XpEntry(day, "session_minutes", s.id, xp))
        total_minutes = sum(s.minutes for s in day_sessions)
        if day.weekday() >= 5 and total_minutes >= table.weekend_min_minutes:
            entries.append(XpEntry(day, "weekend_day", day.isoformat(), table.weekend_active_day))
    for b in facts.blocks:
        entries.append(XpEntry(b.completed_on, "block_completed", b.occurrence_id, table.block_completed))
    for m in facts.missions:
        if m.complete:
            entries.append(XpEntry(m.mission_date, "mission_complete", m.mission_id, table.mission_complete))
        if m.optional_done:
            entries.append(
                XpEntry(m.mission_date, "mission_optional", m.mission_id, m.optional_done * table.mission_optional_item)
            )
    for ws in facts.complete_week_starts:
        entries.append(XpEntry(ws + timedelta(days=6), "week_complete", ws.isoformat(), table.week_complete))
    return sorted(entries, key=lambda e: (e.date, e.source, e.ref_id))


def cumulative_xp(level: int) -> int:
    return 50 * level * (level - 1)


def level_for_xp(total: int, titles: tuple[TitleBand, ...] = DEFAULT_TITLES) -> LevelInfo:
    level = 1
    while cumulative_xp(level + 1) <= total:
        level += 1
    title = next(t.title for t in titles if t.first <= level and (t.last is None or level <= t.last))
    return LevelInfo(level, title, total, total - cumulative_xp(level), 100 * level)
