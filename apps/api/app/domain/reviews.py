"""Revisões por tópico (R07): datas, duplicação, XP e ordem dos cartões. Funções puras."""

from collections.abc import Iterable
from datetime import date, datetime, timedelta

OFFSETS = (1, 7, 21)
DEDUP_DAYS = 2
XP_ON_TIME = 15
XP_LATE = 5
RATINGS = ("nao_lembrei", "palpite", "parcial", "lembrei")
_RATING_RANK = {"nao_lembrei": 0, "palpite": 1, "parcial": 2, None: 3, "lembrei": 4}


def suggest_due_dates(studied_on: date, exam_on: date, offsets: Iterable[int] = OFFSETS) -> list[tuple[int, date]]:
    offsets = tuple(offsets)
    if any(o <= 0 for o in offsets):
        raise ValueError("intervalos de revisão precisam ser positivos")
    dates = [(o, studied_on + timedelta(days=o)) for o in offsets]
    return [(o, d) for o, d in dates if d < exam_on]


def is_duplicate(due_on: date, pending_due_dates: Iterable[date]) -> bool:
    return any(abs((due_on - p).days) <= DEDUP_DAYS for p in pending_due_dates)


def review_xp(due_on: date, completed_on: date) -> int:
    return XP_ON_TIME if completed_on <= due_on else XP_LATE


def card_sort_key(last_rating: str | None, created_at: datetime) -> tuple:
    """Piores avaliações primeiro; cartões nunca avaliados ficam antes dos já lembrados."""
    return (_RATING_RANK[last_rating], created_at)
