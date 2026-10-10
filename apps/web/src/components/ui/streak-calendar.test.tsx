import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { StreakCalendar } from './streak-calendar'

describe('StreakCalendar', () => {
  it('mostra dias neutros, ativos e congelados em pt-BR', () => {
    render(
      <StreakCalendar view="month" month={new Date(2026, 9, 1)} startOfWeek={1}
        streak={[{ periodStart: '2026-10-09', periodEnd: '2026-10-09' },
                 { periodStart: '2026-10-19', periodEnd: '2026-10-19', usedFreeze: true }]}
        neutralDates={['2026-10-10']} />,
    )
    expect(screen.getByText('Seg')).toBeInTheDocument()
    expect(screen.getByRole('gridcell', { name: /10 de outubro.*folga ou fim de semana/ })).toBeInTheDocument()
    expect(screen.getByRole('gridcell', { name: /9 de outubro.*sequência ativa/ })).toBeInTheDocument()
    expect(screen.getByRole('gridcell', { name: /19 de outubro.*congelamento usado/ })).toBeInTheDocument()
  })

  afterEach(() => vi.useRealTimers())

  it('pinta o dia de hoje quando ele já está ativo', () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 9, 9, 15, 0))
    render(<StreakCalendar view="week" startOfWeek={1} streak={[{ periodStart: '2026-10-09', periodEnd: '2026-10-09' }]} />)
    expect(screen.getByRole('gridcell', { name: /9 de outubro, hoje, sequência ativa/ })).toHaveClass('bg-primary')
    expect(screen.getByRole('gridcell', { name: /9 de outubro, hoje/ }).className).not.toMatch(/!bg-primary-foreground/)
  })
})
