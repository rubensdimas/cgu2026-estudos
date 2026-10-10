import { describe, expect, it } from 'vitest'

import { cumulativeXp, levelLines, toLevelsTimeline, toStreakPeriods, toXpSeries } from './adapters'

describe('adaptadores do jogo', () => {
  it('converte dias ativos e congelados em períodos de um dia, ordenados', () => {
    expect(toStreakPeriods({ active_days: ['2026-10-12', '2026-10-09'], frozen_days: ['2026-10-19'], neutral_days: ['2026-10-10'] }))
      .toEqual([
        { periodStart: '2026-10-09', periodEnd: '2026-10-09' },
        { periodStart: '2026-10-12', periodEnd: '2026-10-12' },
        { periodStart: '2026-10-19', periodEnd: '2026-10-19', usedFreeze: true },
      ])
  })

  it('acumula XP por dia, preenchendo dias sem registro', () => {
    const entries = [{ date: '2026-10-09', xp: 75 }, { date: '2026-10-09', xp: 50 }, { date: '2026-10-12', xp: 30 }]
    expect(toXpSeries(entries, '2026-10-09', '2026-10-12')).toEqual([
      { date: '2026-10-09', total: 125, change: 125 },
      { date: '2026-10-10', total: 125, change: 0 },
      { date: '2026-10-11', total: 125, change: 0 },
      { date: '2026-10-12', total: 155, change: 30 },
    ])
  })

  it('toXpSeries ignora lançamentos fora do intervalo', () => {
    const entries = [{ date: '2026-10-09', xp: 10 }, { date: '2026-10-18', xp: 150 }]
    expect(toXpSeries(entries, '2026-10-09', '2026-10-10').map((p) => p.total)).toEqual([10, 10])
  })

  it('calcula limiares de nível iguais aos do backend', () => {
    expect([cumulativeXp(1), cumulativeXp(4), cumulativeXp(18)]).toEqual([0, 600, 15300])
    expect(levelLines(4).map((l) => l.value)).toEqual([600, 1000])
  })

  it('monta a trilha de níveis a partir das faixas de título', () => {
    const items = toLevelsTimeline([
      { from: 1, to: 3, title: 'Estagiário' },
      { from: 18, to: null, title: 'AFFC' },
    ])
    expect(items).toEqual([
      { id: 'nv-1', name: 'Estagiário', description: 'Níveis 1–3', points: 0 },
      { id: 'nv-18', name: 'AFFC', description: 'Nível 18 em diante', points: 15300 },
    ])
  })
})
