from datetime import date, datetime
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("America/Sao_Paulo")


def get_today() -> date:
    """Dependência FastAPI; os testes a substituem por uma data fixa."""
    return datetime.now(TIMEZONE).date()
