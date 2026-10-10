import { addDays } from '@/shared/format'

export interface CalendarDays { active_days: string[]; frozen_days: string[]; neutral_days: string[] }
export interface StreakPeriod { periodStart: string; periodEnd: string; usedFreeze?: boolean }
export interface XpEntry { date: string; xp: number }
export interface XpPoint { date: string; total: number; change: number }
export interface TitleBand { from: number; to: number | null; title: string }
export interface LevelTimelineItem { id: string; name: string; description: string; points: number }

export function toStreakPeriods(cal: CalendarDays): StreakPeriod[] {
  const periods: StreakPeriod[] = [
    ...cal.active_days.map((d) => ({ periodStart: d, periodEnd: d })),
    ...cal.frozen_days.map((d) => ({ periodStart: d, periodEnd: d, usedFreeze: true })),
  ]
  return periods.sort((a, b) => a.periodStart.localeCompare(b.periodStart))
}

/** XP acumulado para estar no nível (mesma fórmula de docs/10 §4). */
export function cumulativeXp(level: number): number {
  return 50 * level * (level - 1)
}

export function toXpSeries(entries: XpEntry[], from: string, to: string): XpPoint[] {
  const byDay = new Map<string, number>()
  for (const e of entries) byDay.set(e.date, (byDay.get(e.date) ?? 0) + e.xp)
  const series: XpPoint[] = []
  let total = 0
  for (let day = from; day <= to; day = addDays(day, 1)) {
    const change = byDay.get(day) ?? 0
    total += change
    series.push({ date: day, total, change })
  }
  return series
}

export function levelLines(level: number): { value: number; color: string }[] {
  return [
    { value: cumulativeXp(level), color: 'var(--muted-foreground)' },
    { value: cumulativeXp(level + 1), color: 'var(--xp)' },
  ]
}

export function toLevelsTimeline(bands: TitleBand[]): LevelTimelineItem[] {
  return bands.map((b) => ({
    id: `nv-${b.from}`,
    name: b.title,
    description: b.to === null ? `Nível ${b.from} em diante` : `Níveis ${b.from}–${b.to}`,
    points: cumulativeXp(b.from),
  }))
}
