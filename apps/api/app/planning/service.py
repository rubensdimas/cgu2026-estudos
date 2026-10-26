import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.cycle import (
    CycleError,
    SlotInput,
    essay_kind_for,
    TemplateInput,
    generate_week,
    next_topic,
    select_template,
    suggest_topic,
    week_index,
    weeks_since,
)
from app.catalog.progress import promote_for_occurrence
from app.errors import ApiError
from app.models import CycleTemplate, Occurrence, StudyPlan, StudySession, Topic, TopicProgress


def current_plan(db: Session) -> StudyPlan:
    plan = db.scalar(select(StudyPlan).order_by(StudyPlan.starts_on.desc()).limit(1))
    if plan is None:
        raise ApiError(404, "plan_missing", "Plano não encontrado. Rode o seed.")
    return plan


def templates(db: Session, plan: StudyPlan) -> list[CycleTemplate]:
    return list(db.scalars(select(CycleTemplate).where(CycleTemplate.study_plan_id == plan.id)))


def to_input(template: CycleTemplate) -> TemplateInput:
    slots = tuple(SlotInput(s.code, s.weekday, s.window, s.minutes, s.purpose) for s in template.slots)
    return TemplateInput(template.effective_from, slots)


def week_occurrences(db: Session, week_start: date) -> list[Occurrence]:
    rows = db.scalars(select(Occurrence).where(Occurrence.week_start == week_start))
    return sorted(rows, key=lambda o: (o.planned_on, o.slot.position))


def ensure_week(db: Session, week_start: date) -> tuple[list[Occurrence], bool]:
    """Gera a semana se ainda não existir. Retorna (ocorrências, criou_agora)."""
    existing = week_occurrences(db, week_start)
    if existing:
        return existing, False
    plan = current_plan(db)
    rows = templates(db, plan)
    try:
        chosen_input = select_template([to_input(t) for t in rows], week_start)
        generated = generate_week(chosen_input, week_start, plan.starts_on, plan.ends_on)
    except CycleError as exc:
        raise ApiError(422, "invalid_week", str(exc), {"week_start": str(exc)}) from exc
    template = next(t for t in rows if t.effective_from == chosen_input.effective_from)
    slot_by_code = {s.code: s for s in template.slots}
    occurrences = [
        Occurrence(
            id=uuid.uuid4(),
            cycle_slot_id=slot_by_code[o.cycle_slot_code].id,
            week_start=o.week_start,
            planned_on=o.planned_on,
            window=o.window,
            status="pending",
        )
        for o in generated
    ]
    db.add_all(occurrences)
    db.flush()
    return week_occurrences(db, week_start), True


def session_stats(db: Session, occurrence_ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[int, date | None]]:
    """Minutos ativos e data de conclusão derivada (maior studied_on) por ocorrência."""
    if not occurrence_ids:
        return {}
    rows = db.execute(
        select(StudySession.occurrence_id, func.sum(StudySession.duration_minutes), func.max(StudySession.studied_on))
        .where(StudySession.occurrence_id.in_(occurrence_ids), StudySession.deleted_at.is_(None))
        .group_by(StudySession.occurrence_id)
    )
    stats: dict[uuid.UUID, tuple[int, date | None]] = defaultdict(lambda: (0, None))
    for occ_id, minutes, last_day in rows:
        stats[occ_id] = (int(minutes), last_day)
    return stats


@dataclass(frozen=True)
class TopicContext:
    topics_by_subject: dict[str, list[str]]
    studied_on: dict[str, date]  # primeira passagem ou revisado, com a data declarada


def topic_context(db: Session) -> TopicContext:
    by_subject: dict[str, list[str]] = defaultdict(list)
    for topic in db.scalars(select(Topic).order_by(Topic.subject_id, Topic.position)):
        by_subject[topic.subject_id].append(topic.id)
    studied = dict(db.execute(select(TopicProgress.topic_id, TopicProgress.declared_on)
                              .where(TopicProgress.status.in_(("first_pass", "reviewed")))).all())
    return TopicContext(dict(by_subject), studied)


def suggested_topic(db: Session, occ: Occurrence, ctx: TopicContext | None = None) -> str | None:
    slot = occ.slot
    if slot.selection_mode != "next_topic_rotation":
        return suggest_topic(slot.selection_mode, slot.candidate_topic_ids,
                             week_index(occ.week_start, current_plan(db).starts_on))
    ctx = ctx or topic_context(db)
    # Só conta o que foi estudado antes do bloco: estudar o tópico hoje não troca a sugestão de hoje.
    done = {t for t, d in ctx.studied_on.items() if d < occ.planned_on}
    effective_from = db.get(CycleTemplate, slot.cycle_template_id).effective_from
    return next_topic(slot.candidate_topic_ids, weeks_since(occ.week_start, effective_from),
                      ctx.topics_by_subject, done)


def occurrence_essay_kind(db: Session, occ: Occurrence) -> str | None:
    """complementary | technical_case nos blocos de discursiva; None nos demais."""
    if occ.slot.activity != "essay":
        return None
    effective_from = db.get(CycleTemplate, occ.slot.cycle_template_id).effective_from
    return essay_kind_for(occ.slot.selection_mode, weeks_since(occ.week_start, effective_from))


def occurrence_out(db: Session, occ: Occurrence, stats: dict, ctx: TopicContext) -> dict:
    minutes, last_day = stats.get(occ.id, (0, None))
    slot = occ.slot
    return {
        "id": str(occ.id),
        "version": occ.version,
        "week_start": occ.week_start,
        "planned_on": occ.planned_on,
        "window": occ.window,
        "status": occ.status,
        "skip_reason": occ.skip_reason,
        "actual_minutes": minutes,
        "completed_on": last_day if occ.status == "completed" else None,
        "slot": {
            "code": slot.code,
            "title": slot.title,
            "purpose": slot.purpose,
            "activity": slot.activity,
            "minutes": slot.minutes,
            "selection_mode": slot.selection_mode,
            "candidate_topic_ids": slot.candidate_topic_ids,
        },
        "suggested_topic_id": suggested_topic(db, occ, ctx),
        "essay_kind": occurrence_essay_kind(db, occ),
    }


def occurrences_out(db: Session, occurrences: list[Occurrence]) -> list[dict]:
    stats = session_stats(db, [o.id for o in occurrences])
    ctx = topic_context(db)
    return [occurrence_out(db, o, stats, ctx) for o in occurrences]


def list_occurrences(db: Session, start: date, end: date) -> list[Occurrence]:
    rows = db.scalars(select(Occurrence).where(Occurrence.planned_on.between(start, end)))
    return sorted(rows, key=lambda o: (o.planned_on, o.slot.position))


def patch_occurrence(db: Session, occ_id: uuid.UUID, patch: dict) -> Occurrence:
    occ = db.get(Occurrence, occ_id)
    if occ is None:
        raise ApiError(404, "not_found", "Bloco não encontrado.")
    if patch["version"] != occ.version:
        raise ApiError(409, "version_conflict", "Este registro foi alterado. Recarregue antes de editar.")
    moving = patch.get("planned_on") is not None or patch.get("window") is not None
    if moving:
        if occ.status != "pending":
            raise ApiError(422, "not_pending", "Só blocos pendentes podem ser remanejados.")
        plan = current_plan(db)
        target = patch.get("planned_on") or occ.planned_on
        if not plan.starts_on <= target <= plan.ends_on:
            raise ApiError(422, "outside_plan", "Data fora do plano.", {"planned_on": "Fora do plano."})
        occ.planned_on = target
        occ.window = patch.get("window") or occ.window
    if patch.get("theme_id") is not None:
        from app.guidance.service import set_theme  # import tardio: guidance depende de planning

        set_theme(db, occ, patch["theme_id"])
    status = patch.get("status")
    if status == "completed":
        minutes, _ = session_stats(db, [occ.id]).get(occ.id, (0, None))
        if minutes == 0:
            raise ApiError(422, "session_required", "Registre uma sessão antes de concluir o bloco.")
    if status == "skipped":
        occ.skip_reason = patch.get("skip_reason")
    if status == "pending":
        occ.skip_reason = None
    if status:
        occ.status = status
    occ.version += 1
    db.flush()
    if status == "completed":
        promote_for_occurrence(db, occ)
    return occ
