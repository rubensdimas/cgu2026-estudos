"""Orientação por bloco: variante de roteiro vigente e rodízio de temas discursivos (B5, B6). Funções puras."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ThemeRef:
    occurrence_id: str
    week_index: int
    stored_theme_id: str | None
    has_session: bool


def _first_free(theme_ids: list[str], start: int, done: set[str]) -> str:
    n = len(theme_ids)
    for k in range(n):
        candidate = theme_ids[(start + k) % n]
        if candidate not in done:
            return candidate
    return theme_ids[start % n]


def resolve_themes(theme_ids: list[str], refs: list[ThemeRef]) -> dict[str, str | None]:
    """Tema de cada ocorrência, em ordem de semana: o tema salvo vence; os demais pegam o tema
    da semana no rodízio, pulando os já feitos (com sessão) em semanas anteriores."""
    if not theme_ids:
        return {r.occurrence_id: None for r in refs}
    done: set[str] = set()
    result: dict[str, str | None] = {}
    for r in sorted(refs, key=lambda r: (r.week_index, r.occurrence_id)):
        if r.has_session and r.stored_theme_id is None:
            # Sessão gravada quando ainda não havia temas: o bloco foi feito sem tema e não gasta o rodízio.
            result[r.occurrence_id] = None
            continue
        if r.stored_theme_id in theme_ids:
            theme = r.stored_theme_id
        else:
            theme = _first_free(theme_ids, r.week_index % len(theme_ids), done)
        result[r.occurrence_id] = theme
        if r.has_session:
            done.add(theme)
    return result


def next_theme(theme_ids: list[str], current: str, done: set[str]) -> str | None:
    """Próximo tema depois de `current` que ainda não foi feito; None se não houver."""
    if current not in theme_ids:
        return None
    n = len(theme_ids)
    start = theme_ids.index(current)
    for k in range(1, n):
        candidate = theme_ids[(start + k) % n]
        if candidate not in done:
            return candidate
    return None


def pick_variant(variants: list[dict], day: date) -> dict:
    """Primeira variante cujo `ate` (inclusivo) não passou; a última tem `ate` nulo."""
    for v in variants:
        if v["ate"] is None or day <= date.fromisoformat(v["ate"]):
            return v
    return variants[-1]
