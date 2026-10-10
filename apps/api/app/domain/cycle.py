"""Geração de semanas do ciclo (R02). Funções puras, sem banco."""

from dataclasses import dataclass
from datetime import date, timedelta

WINDOW_ORDER = {"before": 0, "middle": 1, "after": 2}
ROTATING_MODES = {"alternate_subjects", "rotate_subjects"}


class CycleError(ValueError):
    pass


@dataclass(frozen=True)
class SlotInput:
    code: str
    weekday: int  # 1 = segunda … 5 = sexta
    window: str
    minutes: int
    purpose: str


@dataclass(frozen=True)
class TemplateInput:
    effective_from: date
    slots: tuple[SlotInput, ...]


@dataclass(frozen=True)
class OccurrenceInput:
    cycle_slot_code: str
    week_start: date
    planned_on: date
    window: str
    status: str = "pending"


def week_start_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def select_template(templates: list[TemplateInput], week_start: date) -> TemplateInput:
    valid = [t for t in templates if t.effective_from <= week_start]
    if not valid:
        raise CycleError("Nenhum template vigente para esta semana.")
    return max(valid, key=lambda t: t.effective_from)


def generate_week(
    template: TemplateInput, week_start: date, plan_starts_on: date, plan_ends_on: date
) -> list[OccurrenceInput]:
    if week_start.weekday() != 0:
        raise CycleError("A semana deve começar numa segunda-feira.")
    if week_start + timedelta(days=6) < plan_starts_on or week_start > plan_ends_on:
        raise CycleError("Semana fora do período do plano.")
    if template.effective_from > week_start:
        raise CycleError("Template ainda não vigente nesta semana.")
    slots = sorted(template.slots, key=lambda s: (s.weekday, WINDOW_ORDER[s.window]))
    result = []
    for slot in slots:
        planned_on = week_start + timedelta(days=slot.weekday - 1)
        if plan_starts_on <= planned_on <= plan_ends_on:
            result.append(OccurrenceInput(slot.code, week_start, planned_on, slot.window))
    return result


def week_index(week_start: date, plan_starts_on: date) -> int:
    """0 = semana que contém o início do plano (parcial); 1 = primeira semana cheia."""
    return (week_start - week_start_of(plan_starts_on)).days // 7


def suggest_topic(selection_mode: str, candidates: list[str], index: int) -> str | None:
    """Semanas ímpares usam o primeiro candidato; pares, o segundo (02 §3)."""
    if not candidates:
        return None
    if selection_mode in ROTATING_MODES:
        return candidates[(index - 1) % len(candidates)]
    if selection_mode == "alternate_delivery_and_interfaces_ai":
        delivery = [c for c in candidates if c.startswith("E04")]
        interfaces = [c for c in candidates if not c.startswith("E04")]
        group = delivery if index % 2 == 1 else interfaces
        return (group or candidates)[0]
    return candidates[0]
