import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StreakCard } from './streak-card'

describe('StreakCard', () => {
  it('concorda singular e plural dos dias úteis', () => {
    render(<StreakCard streak={[]} currentStreak={1} longestStreak={5} total={0} />)
    expect(screen.getByText('dia útil')).toBeInTheDocument()
    expect(screen.getByText('dias úteis')).toBeInTheDocument()
  })
})
