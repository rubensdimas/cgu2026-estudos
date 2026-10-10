from datetime import date, datetime, timezone

from app import clock


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 10, 2, 30, tzinfo=timezone.utc).astimezone(tz)


def test_today_uses_sao_paulo_civil_date(monkeypatch):
    monkeypatch.setattr(clock, "datetime", FrozenDatetime)
    assert clock.get_today() == date(2026, 10, 9)
