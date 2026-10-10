import type { Window } from './api/types'

export const WINDOW_LABEL: Record<Window, string> = { before: 'Antes', middle: 'Intermediário', after: 'Depois' }

export const PURPOSE_LABEL = {
  specific: 'Específicos',
  basic: 'Básicos',
  complementary: 'Complementares',
  essay: 'Discursiva',
} as const

export const XP_SOURCE_LABEL: Record<string, string> = {
  session_minutes: 'minutos de estudo',
  block_completed: 'bloco concluído',
  mission_complete: 'missão completa',
  mission_optional: 'item bônus',
  weekend_day: 'dia extra',
  week_complete: 'semana completa',
}

export function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

export function mondayOf(iso: string): string {
  const d = new Date(`${iso}T12:00:00Z`)
  return addDays(iso, -((d.getUTCDay() + 6) % 7))
}

export function formatDay(iso: string): string {
  return new Date(`${iso}T12:00:00Z`).toLocaleDateString('pt-BR', {
    weekday: 'short', day: '2-digit', month: '2-digit', timeZone: 'UTC',
  })
}
