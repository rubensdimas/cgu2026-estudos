"""Orientação de um bloco: roteiro, tópico, materiais e tema discursivo (spec B1–B6)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.cycle import suggest_topic, week_index
from app.domain.guidance import ThemeRef, next_theme, pick_variant, resolve_themes
from app.errors import ApiError
from app.guidance import content
from app.models import CycleSlot, Occurrence, Topic
from app.planning.service import current_plan, session_stats


def essay_kind(occ: Occurrence) -> str | None:
    """complementary | technical_case para S14/S15; None para os demais."""
    return occ.slot.selection_mode if occ.slot.activity == "essay" else None


def _theme_ids(kind: str) -> list[str]:
    return [t["id"] for t in content.guidance()["temas"][kind]]


def _theme_state(db: Session, kind: str) -> tuple[dict[str, str | None], set[str], set[str]]:
    """(tema por ocorrência, temas feitos, ocorrências com sessão)."""
    plan = current_plan(db)
    occs = list(db.scalars(
        select(Occurrence).join(CycleSlot).where(CycleSlot.activity == "essay", CycleSlot.selection_mode == kind)
    ))
    stats = session_stats(db, [o.id for o in occs])
    with_session = {str(o.id) for o in occs if stats.get(o.id, (0, None))[0] > 0}
    refs = [ThemeRef(str(o.id), week_index(o.week_start, plan.starts_on), o.theme_id, str(o.id) in with_session)
            for o in occs]
    resolved = resolve_themes(_theme_ids(kind), refs)
    done = {resolved[oid] for oid in with_session if resolved[oid] is not None}
    return resolved, done, with_session


def current_theme(db: Session, occ: Occurrence) -> str | None:
    kind = essay_kind(occ)
    if kind is None:
        return None
    resolved, _, _ = _theme_state(db, kind)
    return resolved.get(str(occ.id))


def set_theme(db: Session, occ: Occurrence, theme_id: str) -> None:
    kind = essay_kind(occ)
    if kind is None or theme_id not in _theme_ids(kind):
        raise ApiError(422, "unknown_theme", "Tema inexistente para este bloco.", {"theme_id": "Inexistente."})
    _, _, with_session = _theme_state(db, kind)
    if str(occ.id) in with_session:
        raise ApiError(422, "theme_locked", "Este bloco já tem sessão registrada: o tema ficou fixo.")
    occ.theme_id = theme_id


def guidance_out(db: Session, occ: Occurrence) -> dict:
    data = content.guidance()
    slot = occ.slot
    idx = week_index(occ.week_start, current_plan(db).starts_on)
    variants = data["roteiros_por_bloco"].get(slot.code) or data["roteiros_por_atividade"][slot.activity]
    topic_id = suggest_topic(slot.selection_mode, slot.candidate_topic_ids, idx)
    topic = db.get(Topic, topic_id) if topic_id else None
    out = {
        "roteiro": pick_variant(variants, occ.planned_on),
        "nota": data["primeira_semana"].get(slot.code) if idx == 0 else None,
        "topic": {"id": topic.id, "title": topic.title, "subitens": data["subitens"].get(topic.id, [])}
        if topic else None,
        "materiais": data["materiais"].get(topic_id, []) if topic_id else [],
        "tema": None,
        "next_theme_id": None,
        "lembretes": [],
    }
    kind = essay_kind(occ)
    if kind is None:
        return out
    resolved, done, with_session = _theme_state(db, kind)
    themes = {t["id"]: t for t in data["temas"][kind]}
    current = resolved.get(str(occ.id))
    out["tema"] = themes.get(current) if current else None
    out["lembretes"] = data["lembretes"][kind]
    if current and str(occ.id) not in with_session:
        out["next_theme_id"] = next_theme(list(themes), current, done)
    return out
