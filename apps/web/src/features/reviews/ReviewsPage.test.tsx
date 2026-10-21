import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Review } from '../../shared/api/types'
import { renderWithProviders, stubFetch } from '../../test/render'
import { ReviewsPage } from './ReviewsPage'

const review = (id: string, topic: string, due_on: string, late = false): Review => ({
  id, version: 1, session_id: 's', topic_id: topic, offset_days: 1, due_on, status: 'pending', completed_on: null, late,
  cards_count: 2,
})

afterEach(() => vi.unstubAllGlobals())

describe('ReviewsPage', () => {
  it('agrupa em atrasadas, hoje e próximas', async () => {
    stubFetch([
      { match: '/game/summary', body: { today: '2026-10-21' } },
      { match: '/subjects', body: { items: [], total: 0 } },
      { match: '/reviews', body: { total: 3, items: [
        review('a', 'C02.01', '2026-10-19', true), review('b', 'C03.01', '2026-10-21'), review('c', 'E02.01', '2026-10-27'),
      ] } },
    ])
    renderWithProviders(<ReviewsPage />)
    const late = await screen.findByRole('region', { name: 'Atrasadas' })
    expect(within(late).getByText(/C02\.01/)).toBeInTheDocument()
    expect(within(screen.getByRole('region', { name: 'Hoje' })).getByText(/C03\.01/)).toBeInTheDocument()
    expect(within(screen.getByRole('region', { name: 'Próximas' })).getByText(/E02\.01/)).toBeInTheDocument()
    expect(within(late).getByRole('link', { name: /Revisar/ })).toHaveAttribute('href', '/revisoes/a')
  })
})
