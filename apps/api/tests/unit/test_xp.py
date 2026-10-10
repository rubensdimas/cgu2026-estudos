from datetime import date

import pytest

from app.domain.weeks import is_week_complete, minutes_goal_for_week
from app.domain.xp import (
    BlockFact,
    GameFacts,
    MissionFact,
    SessionFact,
    XpTable,
    level_for_xp,
    xp_ledger,
)

FRI, SAT = date(2026, 10, 9), date(2026, 10, 10)
T = XpTable()


def total(facts: GameFacts) -> int:
    return sum(e.xp for e in xp_ledger(facts, T))


def test_session_block_and_mission_same_day():
    facts = GameFacts(
        sessions=(SessionFact("s1", FRI, 50),),
        blocks=(BlockFact("o1", FRI),),
        missions=(MissionFact("m1", FRI, complete=True, optional_done=0),),
    )
    assert total(facts) == 120


def test_daily_minutes_cap():
    facts = GameFacts(sessions=(SessionFact("a", FRI, 200), SessionFact("b", FRI, 100)))
    assert total(facts) == 240


def test_no_records_no_xp():
    assert xp_ledger(GameFacts(), T) == []


def test_optional_items_and_weekend_bonus():
    facts = GameFacts(
        sessions=(SessionFact("s", SAT, 45),),
        missions=(MissionFact("m", SAT, complete=False, optional_done=1),),
    )
    assert total(facts) == 45 + 20 + 10


def test_weekend_below_minimum_has_no_bonus():
    assert total(GameFacts(sessions=(SessionFact("s", SAT, 29),))) == 29


def test_week_complete_dated_on_sunday():
    entries = xp_ledger(GameFacts(complete_week_starts=frozenset({date(2026, 10, 12)})), T)
    assert [(e.date, e.source, e.xp) for e in entries] == [(date(2026, 10, 18), "week_complete", 150)]


@pytest.mark.parametrize(
    ("xp", "level", "title"),
    [(0, 1, "Estagiário"), (99, 1, "Estagiário"), (100, 2, "Estagiário"), (300, 3, "Estagiário"),
     (600, 4, "Analista"), (15300, 18, "AFFC")],
)
def test_levels(xp, level, title):
    info = level_for_xp(xp)
    assert (info.level, info.title) == (level, title)


def test_level_progress_fields():
    info = level_for_xp(150)
    assert (info.level, info.xp_into_level, info.xp_for_next) == (2, 50, 200)


def test_week_completion_rules():
    assert minutes_goal_for_week(date(2026, 10, 5), date(2026, 10, 9), 180, 900) == 180
    assert minutes_goal_for_week(date(2026, 10, 12), date(2026, 10, 9), 900, 900) == 900
    assert is_week_complete(["completed"] * 3, 0, 180)
    assert not is_week_complete(["completed", "skipped"], 100, 900)
    assert is_week_complete(["completed", "skipped"], 900, 900)
    assert not is_week_complete([], 0, 0)
