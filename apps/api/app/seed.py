"""Carga idempotente de docs/data. Atualiza catálogo; nunca sobrescreve settings nem dados pessoais."""

import json
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.db import SessionLocal
from app.models import AppSettings, CycleSlot, CycleTemplate, ExamVersion, StudyPlan, Subject, Topic

NAMESPACE = uuid.UUID("6b0d6c8e-2f1a-4c55-9c3e-0c6f5b0a2026")


def stable_id(*parts: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, "/".join(parts))


def load(name: str) -> dict:
    return json.loads((config.DATA_DIR / name).read_text(encoding="utf-8"))


def seed(db: Session) -> None:
    catalog, cycle, game = load("catalogo-edital.json"), load("ciclo-inicial.json"), load("gamificacao.json")
    exam = cycle["exam"]
    source = catalog["source"]

    version = db.get(ExamVersion, catalog["exam_version_id"])
    if version is None:
        version = ExamVersion(
            id=catalog["exam_version_id"],
            exam_id=catalog["exam_id"],
            title=source["title"],
            publication_date=date.fromisoformat(source["publication_date"]),
            source_url=source["url"],
            source_sha256=source["sha256"],
            exam_date=date.fromisoformat(exam["exam_date"]),
            scoring_rules=exam,
        )
        db.add(version)
        db.flush()

    for s_pos, s in enumerate(catalog["subjects"]):
        subject = db.get(Subject, s["id"]) or Subject(id=s["id"], exam_version_id=version.id)
        subject.paper, subject.title, subject.source_ref, subject.position = s["paper"], s["title"], s["source_ref"], s_pos
        db.add(subject)
        for t_pos, t in enumerate(s["topics"]):
            topic = db.get(Topic, t["id"]) or Topic(id=t["id"], subject_id=s["id"])
            topic.title, topic.source_ref, topic.is_summary, topic.position = (
                t["title"], t["source_ref"], t["is_summary"], t_pos,
            )
            db.add(topic)
    db.flush()

    plan_id = stable_id("plan", version.id)
    plan = db.get(StudyPlan, plan_id)
    if plan is None:
        plan = StudyPlan(
            id=plan_id,
            exam_version_id=version.id,
            starts_on=date.fromisoformat(cycle["starts_on"]),
            ends_on=date.fromisoformat(cycle["ends_on"]),
        )
        db.add(plan)
        db.flush()

    effective_from = date.fromisoformat(cycle["template"]["effective_from"])
    template = db.scalar(
        select(CycleTemplate).where(
            CycleTemplate.study_plan_id == plan.id, CycleTemplate.effective_from == effective_from
        )
    )
    if template is None:
        template_id = stable_id("template", str(plan.id), effective_from.isoformat())
        template = CycleTemplate(
            id=template_id,
            study_plan_id=plan.id,
            effective_from=effective_from,
            weekly_minutes=cycle["weekly_minutes"],
            origin=cycle["template"]["origin"],
        )
        template.slots = [
            CycleSlot(
                id=stable_id("slot", str(template_id), s["code"]),
                code=s["code"],
                weekday=s["weekday"],
                window=s["window"],
                minutes=s["minutes"],
                purpose=s["purpose"],
                activity=s["activity"],
                title=s["title"],
                selection_mode=s["selection_mode"],
                candidate_topic_ids=s["candidate_topic_ids"],
                position=i,
            )
            for i, s in enumerate(cycle["slots"])
        ]
        db.add(template)

    if db.get(AppSettings, 1) is None:
        d = game["settings_defaults"]
        db.add(
            AppSettings(
                id=1,
                timezone=d["timezone"],
                weekly_goals=d["weekly_goals"],
                daily_question_goal=d["daily_question_goal"],
                streak_min_minutes=d["streak_min_minutes"],
                max_freezes=d["max_freezes"],
            )
        )
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed(db)
    print("seed ok")


if __name__ == "__main__":
    main()
