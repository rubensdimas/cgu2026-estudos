"""Semana completa e meta de minutos da semana ([10] §3 e §6)."""

from datetime import date


def minutes_goal_for_week(
    week_start: date, plan_starts_on: date, generated_minutes: int, default_goal: int
) -> int:
    """Semana inicial parcial usa a soma dos blocos gerados; as demais, a meta configurada."""
    return generated_minutes if week_start < plan_starts_on else default_goal


def is_week_complete(occurrence_statuses: list[str], actual_minutes: int, minutes_goal: int) -> bool:
    if occurrence_statuses and all(s == "completed" for s in occurrence_statuses):
        return True
    return minutes_goal > 0 and actual_minutes >= minutes_goal
