from datetime import date, datetime

import pytest

from app.domain.reviews import card_sort_key, is_duplicate, review_xp, suggest_due_dates

EXAM = date(2026, 12, 13)


def test_due_dates_follow_offsets():
    assert suggest_due_dates(date(2026, 10, 12), EXAM) == [
        (1, date(2026, 10, 13)), (7, date(2026, 10, 19)), (21, date(2026, 11, 2)),
    ]


def test_due_dates_skip_after_exam():
    assert [o for o, _ in suggest_due_dates(date(2026, 12, 1), EXAM)] == [1, 7]
    assert suggest_due_dates(date(2026, 12, 12), EXAM) == []


@pytest.mark.parametrize("offsets", [(0,), (-1,)])
def test_offsets_must_be_positive(offsets):
    with pytest.raises(ValueError):
        suggest_due_dates(date(2026, 10, 12), EXAM, offsets)


def test_duplicate_within_two_days():
    pending = [date(2026, 10, 20)]
    assert is_duplicate(date(2026, 10, 22), pending)
    assert is_duplicate(date(2026, 10, 18), pending)
    assert not is_duplicate(date(2026, 10, 23), pending)


def test_review_xp_on_time_and_late():
    due = date(2026, 10, 20)
    assert review_xp(due, date(2026, 10, 19)) == 15
    assert review_xp(due, due) == 15
    assert review_xp(due, date(2026, 10, 21)) == 5


def test_card_order_worst_first():
    t = datetime(2026, 10, 20)
    ratings = ["lembrei", None, "palpite", "nao_lembrei", "parcial"]
    assert sorted(ratings, key=lambda r: card_sort_key(r, t)) == ["nao_lembrei", "palpite", "parcial", None, "lembrei"]
