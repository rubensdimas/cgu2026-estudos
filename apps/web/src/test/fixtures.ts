import type { Summary } from '../shared/api/types'

export const summary: Summary = {
  today: '2026-10-14', exam_date: '2026-12-13', days_to_exam: 60, xp_total: 300, level: 2, title: 'Estagiário',
  xp_into_level: 100, xp_for_next: 250,
  streak: { current: 3, best: 5, freezes_available: 1, frozen_days: [], at_stake_today: false, minutes_today: 0, min_minutes: 30 },
  holiday_suggestion: null,
}

/** Corpo de erro no formato da API. */
export const errorBody = (message: string, code = 'unknown') => ({ error: { code, message } })
