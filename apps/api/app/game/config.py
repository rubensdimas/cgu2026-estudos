import json
from functools import lru_cache

from app import config
from app.domain.xp import TitleBand, XpTable


@lru_cache
def game_config() -> dict:
    return json.loads((config.DATA_DIR / "gamificacao.json").read_text(encoding="utf-8"))


def xp_table(streak_min_minutes: int) -> XpTable:
    xp = game_config()["xp"]
    return XpTable(
        per_session_minute=xp["per_session_minute"],
        session_minutes_daily_cap=xp["session_minutes_daily_cap"],
        block_completed=xp["block_completed"],
        mission_complete=xp["mission_complete"],
        mission_optional_item=xp["mission_optional_item"],
        week_complete=xp["week_complete"],
        weekend_active_day=xp["weekend_active_day"],
        weekend_min_minutes=streak_min_minutes,
    )


def titles() -> tuple[TitleBand, ...]:
    return tuple(TitleBand(t["from"], t["to"], t["title"]) for t in game_config()["levels"]["titles"])


def holiday_suggestions() -> list[dict]:
    return game_config().get("holiday_suggestions", [])
