"""Modelos ORM da F1. Valores derivados (XP, sequência, conclusão de missão) não têm coluna."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

WINDOWS = "'before','middle','after'"


class Versioned:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class ExamVersion(Base):
    __tablename__ = "exam_versions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    exam_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text)
    publication_date: Mapped[date] = mapped_column(Date)
    source_url: Mapped[str] = mapped_column(Text)
    source_sha256: Mapped[str] = mapped_column(String(64))
    exam_date: Mapped[date] = mapped_column(Date)
    scoring_rules: Mapped[dict] = mapped_column(JSONB)


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    exam_version_id: Mapped[str] = mapped_column(ForeignKey("exam_versions.id"))
    paper: Mapped[str] = mapped_column(String(2))
    title: Mapped[str] = mapped_column(Text)
    source_ref: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    topics: Mapped[list["Topic"]] = relationship(order_by="Topic.position")


class Topic(Base):
    __tablename__ = "topics"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"))
    title: Mapped[str] = mapped_column(Text)
    source_ref: Mapped[str] = mapped_column(Text)
    is_summary: Mapped[bool] = mapped_column(Boolean)
    position: Mapped[int] = mapped_column(Integer)


class TopicProgress(Versioned, Base):
    __tablename__ = "topic_progress"
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(16))
    declared_on: Mapped[date] = mapped_column(Date)
    __table_args__ = (
        CheckConstraint(
            "status in ('not_started','in_progress','first_pass','reviewed')", name="ck_topic_progress_status"
        ),
    )


class AppSettings(Versioned, Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timezone: Mapped[str] = mapped_column(String(64))
    weekly_goals: Mapped[dict] = mapped_column(JSONB)
    daily_question_goal: Mapped[int] = mapped_column(Integer)
    streak_min_minutes: Mapped[int] = mapped_column(Integer)
    max_freezes: Mapped[int] = mapped_column(Integer)
    __table_args__ = (CheckConstraint("id = 1", name="ck_settings_singleton"),)


class StudyPlan(Base):
    __tablename__ = "study_plans"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    exam_version_id: Mapped[str] = mapped_column(ForeignKey("exam_versions.id"))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    exam_version: Mapped[ExamVersion] = relationship()


class CycleTemplate(Base):
    __tablename__ = "cycle_templates"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    study_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("study_plans.id"))
    effective_from: Mapped[date] = mapped_column(Date)
    weekly_minutes: Mapped[int] = mapped_column(Integer)
    origin: Mapped[str] = mapped_column(String(16))
    slots: Mapped[list["CycleSlot"]] = relationship(order_by="CycleSlot.position", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("study_plan_id", "effective_from", name="uq_template_plan_effective"),)


class CycleSlot(Base):
    __tablename__ = "cycle_slots"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    cycle_template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cycle_templates.id"))
    code: Mapped[str] = mapped_column(String(8))
    weekday: Mapped[int] = mapped_column(Integer)
    window: Mapped[str] = mapped_column(String(8))
    minutes: Mapped[int] = mapped_column(Integer)
    purpose: Mapped[str] = mapped_column(String(16))
    activity: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(Text)
    selection_mode: Mapped[str] = mapped_column(String(48))
    candidate_topic_ids: Mapped[list[str]] = mapped_column(JSONB)
    position: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("cycle_template_id", "code", name="uq_slot_template_code"),)


class Occurrence(Versioned, Base):
    __tablename__ = "occurrences"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cycle_slot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cycle_slots.id"))
    week_start: Mapped[date] = mapped_column(Date)
    planned_on: Mapped[date] = mapped_column(Date, index=True)
    window: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    skip_reason: Mapped[str | None] = mapped_column(Text)
    theme_id: Mapped[str | None] = mapped_column(String(16))
    slot: Mapped[CycleSlot] = relationship(lazy="joined")
    __table_args__ = (
        UniqueConstraint("cycle_slot_id", "week_start", name="uq_occurrence_slot_week"),
        CheckConstraint("status in ('pending','completed','skipped')", name="ck_occurrence_status"),
        CheckConstraint(f"\"window\" in ({WINDOWS})", name="ck_occurrence_window"),
    )


class SessionTopic(Base):
    __tablename__ = "session_topics"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("study_sessions.id"), primary_key=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), primary_key=True)


class StudySession(Versioned, Base):
    __tablename__ = "study_sessions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    occurrence_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("occurrences.id"), index=True)
    studied_on: Mapped[date] = mapped_column(Date, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    activity: Mapped[str] = mapped_column(String(16))
    essay_kind: Mapped[str | None] = mapped_column(String(16))
    notes: Mapped[str] = mapped_column(Text, default="")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    topic_links: Mapped[list[SessionTopic]] = relationship(
        cascade="all, delete-orphan", order_by=SessionTopic.topic_id, lazy="selectin"
    )
    __table_args__ = (
        CheckConstraint("duration_minutes between 1 and 720", name="ck_session_duration"),
        CheckConstraint("activity in ('theory','questions','review','essay')", name="ck_session_activity"),
        CheckConstraint("activity <> 'essay' or essay_kind is not null", name="ck_session_essay_kind"),
    )

    @property
    def topic_ids(self) -> list[str]:
        return [link.topic_id for link in self.topic_links]


class DailyMission(Base):
    __tablename__ = "daily_missions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    mission_date: Mapped[date] = mapped_column(Date, unique=True)
    kind: Mapped[str] = mapped_column(String(8))
    checkout_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    items: Mapped[list["MissionItem"]] = relationship(
        order_by="MissionItem.position", cascade="all, delete-orphan", lazy="selectin"
    )


class MissionItem(Base):
    __tablename__ = "mission_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("daily_missions.id"))
    position: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))
    ref_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    target: Mapped[int | None] = mapped_column(Integer)
    required: Mapped[bool] = mapped_column(Boolean)
    na_reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("mission_id", "position", name="uq_mission_item_position"),)


class DayOff(Base):
    __tablename__ = "day_offs"
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    reason: Mapped[str] = mapped_column(Text)


class FlashcardBatch(Base):
    __tablename__ = "flashcard_batches"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("study_sessions.id"), primary_key=True)
    model: Mapped[str] = mapped_column(String(64))
    studied: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(Text)
    focus: Mapped[str] = mapped_column(Text)
    priorities: Mapped[list[str]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Flashcard(Versioned, Base):
    __tablename__ = "flashcards"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("study_sessions.id"), index=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), index=True)
    subitem: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(24))
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    last_rating: Mapped[str | None] = mapped_column(String(16))
    rated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("status in ('draft','approved')", name="ck_flashcard_status"),
        CheckConstraint(
            "last_rating is null or last_rating in ('nao_lembrei','palpite','parcial','lembrei')",
            name="ck_flashcard_rating"),
        CheckConstraint(
            "category in ('conceito','distincao','condicao','causa_consequencia','aplicacao','erro_recorrente',"
            "'fundamentacao')", name="ck_flashcard_category"),
    )


class ReviewTask(Versioned, Base):
    __tablename__ = "review_tasks"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("study_sessions.id"), index=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), index=True)
    offset_days: Mapped[int] = mapped_column(Integer)
    due_on: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    completed_on: Mapped[date | None] = mapped_column(Date)
    closed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("review_tasks.id"))
    __table_args__ = (
        UniqueConstraint("session_id", "topic_id", "offset_days", name="uq_review_session_topic_offset"),
        CheckConstraint("status in ('pending','completed','dismissed')", name="ck_review_status"),
        CheckConstraint("offset_days > 0", name="ck_review_offset"),
    )

