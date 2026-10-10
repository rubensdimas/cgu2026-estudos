export type Window = 'before' | 'middle' | 'after'
export type OccurrenceStatus = 'pending' | 'completed' | 'skipped'
export type Activity = 'theory' | 'questions' | 'review' | 'essay'
export type EssayKind = 'complementary' | 'technical_case'

export interface XpDeltaEntry { source: string; ref_id: string; date: string; xp: number }

export interface GameDelta {
  xp_gained: number
  entries: XpDeltaEntry[]
  level_up: number | null
  mission_complete: string[]
  streak: number
}

export interface Summary {
  today: string
  exam_date: string
  days_to_exam: number
  xp_total: number
  level: number
  title: string
  xp_into_level: number
  xp_for_next: number
  streak: {
    current: number
    best: number
    freezes_available: number
    frozen_days: string[]
    at_stake_today: boolean
    minutes_today: number
    min_minutes: number
  }
  holiday_suggestion: { date: string; label: string } | null
}

export interface Slot {
  code: string
  title: string
  purpose: 'specific' | 'basic' | 'complementary' | 'essay'
  activity: Activity
  minutes: number
  selection_mode: string
  candidate_topic_ids: string[]
}

export interface Occurrence {
  id: string
  version: number
  week_start: string
  planned_on: string
  window: Window
  status: OccurrenceStatus
  skip_reason: string | null
  actual_minutes: number
  completed_on: string | null
  slot: Slot
  suggested_topic_id: string | null
}

export interface MissionItem {
  id: string
  position: number
  kind: 'block' | 'review' | 'questions' | 'checkout'
  ref_id: string | null
  required: boolean
  target: number | null
  state: 'pending' | 'done' | 'not_applicable'
  na_reason: string | null
}

export interface Mission {
  id: string
  date: string
  kind: 'weekday' | 'free'
  checkout_note: string | null
  complete: boolean
  items: MissionItem[]
}

export interface DayView {
  date: string
  kind: 'weekday' | 'free'
  in_plan: boolean
  week_generated: boolean
  occurrences: Occurrence[]
  mission: Mission | null
  xp_today: number
}

export interface Topic {
  id: string
  title: string
  source_ref: string
  progress: { status: string; declared_on: string; version: number } | null
}

export interface Subject { id: string; paper: 'P1' | 'P2' | 'P3'; title: string; topics: Topic[] }

export interface SessionInput {
  id: string
  occurrence_id: string | null
  studied_on: string
  duration_minutes: number
  activity: Activity
  essay_kind: EssayKind | null
  topic_ids: string[]
  notes: string
  complete_occurrence: boolean
}

export interface WithDelta { game_delta: GameDelta }

export interface ListResponse<T> { items: T[]; total: number }

export interface DayOff { day: string; reason: string }
