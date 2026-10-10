from datetime import date, timedelta

from app.domain.streak import streak_state

START = date(2026, 10, 9)


def d(month: int, day: int) -> date:
    return date(2026, month, day)


def test_streak_breaks_without_freeze():
    s = streak_state({d(10, 9): 45, d(10, 12): 30}, set(), set(), START, d(10, 14))
    assert (s.current, s.best, s.frozen_days) == (0, 2, ())


def test_day_off_is_neutral():
    s = streak_state({d(10, 9): 45, d(10, 12): 30}, {d(10, 13)}, set(), START, d(10, 14))
    assert s.current == 2
    assert s.at_stake_today is True


def test_weekend_never_breaks():
    s = streak_state({d(10, 9): 60}, set(), set(), START, d(10, 12))
    assert s.current == 1


def test_today_in_play_does_not_change_streak():
    s = streak_state({d(10, 9): 60, d(10, 12): 10}, set(), set(), START, d(10, 12))
    assert (s.current, s.at_stake_today, s.minutes_today) == (1, True, 10)


def test_today_reaching_minimum_counts():
    s = streak_state({d(10, 9): 60, d(10, 12): 30}, set(), set(), START, d(10, 12))
    assert (s.current, s.at_stake_today) == (2, False)


def test_complete_week_grants_freeze_that_covers_next_missed_day():
    minutes = {d(10, 12) + timedelta(days=i): 60 for i in range(5)}
    s = streak_state(minutes, set(), {d(10, 12)}, START, d(10, 20))
    assert s.current == 5
    assert s.frozen_days == (d(10, 19),)
    assert s.freezes_available == 0


def test_freezes_capped_at_two():
    weeks = {d(10, 12), d(10, 19), d(10, 26)}
    minutes = {}
    for ws in weeks:
        for i in range(5):
            minutes[ws + timedelta(days=i)] = 60
    s = streak_state(minutes, set(), weeks, START, d(11, 2))
    assert s.freezes_available == 2


def test_before_plan_start_nothing_counts():
    s = streak_state({}, set(), set(), START, d(10, 8))
    assert (s.current, s.at_stake_today) == (0, False)
