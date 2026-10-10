"""Sequência de dias úteis com folgas e congelamentos ([10] §5)."""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class StreakState:
    current: int
    best: int
    freezes_available: int
    frozen_days: tuple[date, ...]
    at_stake_today: bool
    minutes_today: int


def streak_state(
    minutes_by_date: dict[date, int],
    day_offs: set[date],
    complete_week_starts: set[date],
    start: date,
    today: date,
    min_minutes: int = 30,
    max_freezes: int = 2,
) -> StreakState:
    current = best = freezes = 0
    frozen: list[date] = []
    day = start
    while day < today:
        if day.weekday() < 5 and day not in day_offs:
            if minutes_by_date.get(day, 0) >= min_minutes:
                current += 1
                best = max(best, current)
            elif freezes > 0:
                freezes -= 1
                frozen.append(day)
            else:
                current = 0
        if day.weekday() == 6 and day - timedelta(days=6) in complete_week_starts:
            freezes = min(max_freezes, freezes + 1)
        day += timedelta(days=1)

    minutes_today = minutes_by_date.get(today, 0)
    counts_today = today >= start and today.weekday() < 5 and today not in day_offs
    at_stake = False
    if counts_today and minutes_today >= min_minutes:
        current += 1
        best = max(best, current)
    elif counts_today:
        at_stake = True
    return StreakState(current, best, freezes, tuple(frozen), at_stake, minutes_today)
