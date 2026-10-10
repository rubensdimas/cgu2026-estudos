import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StreakCard } from './streak-card'

describe('StreakCard', () => {
  it('concorda singular e plural dos dias úteis', () => {
    render(<StreakCard streak={[]} currentStreak={1} longestStreak={5} total={0} />)
    expect(screen.getByText('dia útil')).toBeInTheDocument()
    expect(screen.getByText('dias úteis')).toBeInTheDocument()
  })

  it('não cria botão sem nome quando não há ação', () => {
    render(<StreakCard streak={[]} currentStreak={0} longestStreak={0} total={0} />)
    expect(screen.getAllByRole('button').map((b) => b.textContent)).toEqual(['Como funciona a sequência?'])
  })
})
