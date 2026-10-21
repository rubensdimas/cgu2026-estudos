import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Flashcard, ReviewDetail } from '../../shared/api/types'
import { renderWithProviders, stubFetch } from '../../test/render'
import { ReviewSession } from './ReviewSession'

const card = (id: string, front: string): Flashcard => ({
  id, version: 2, session_id: 's1', topic_id: 'C02.01', subitem: '1.1', category: 'conceito', front, back: `Verso de ${front}`,
  status: 'approved', last_rating: null,
})

const review = (cards: Flashcard[]): ReviewDetail => ({
  id: 'r1', version: 1, session_id: 's1', topic_id: 'C02.01', offset_days: 1, due_on: '2026-10-21', status: 'pending',
  completed_on: null, late: false, cards_count: cards.length, cards,
})

const subjects = [{ id: 'C02', paper: 'P2', title: 'Transparência', source_ref: '', topics: [
  { id: 'C02.01', title: 'Acesso à informação', source_ref: '', progress: null },
] }]
const delta = { xp_gained: 15, entries: [], level_up: null, mission_complete: [], streak: 1 }

function stub(detail: ReviewDetail) {
  return stubFetch([
    { match: '/game/summary', body: { today: '2026-10-21' } },
    { match: '/subjects', body: { items: subjects, total: 1 } },
    { method: 'POST', match: '/reviews/r1/complete', body: { ...detail, status: 'completed', game_delta: delta } },
    { match: '/reviews/r1', body: detail },
    { method: 'PUT', match: '/rating', body: {} },
  ])
}

afterEach(() => vi.unstubAllGlobals())

describe('ReviewSession', () => {
  it('revela o verso, avalia e passa ao próximo cartão', async () => {
    const fetchMock = stub(review([card('c1', 'Primeira'), card('c2', 'Segunda')]))
    renderWithProviders(<ReviewSession reviewId="r1" />)
    const user = userEvent.setup()
    expect(await screen.findByText('Primeira')).toBeInTheDocument()
    expect(screen.queryByText('Verso de Primeira')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Mostrar verso' }))
    expect(screen.getByText('Verso de Primeira')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Não lembrei' }))
    expect(await screen.findByText('Segunda')).toBeInTheDocument()
    const rating = fetchMock.mock.calls.find(([u]) => String(u).includes('/flashcards/c1/rating'))!
    expect(JSON.parse(rating[1]!.body as string)).toEqual({ rating: 'nao_lembrei' })
  })

  it('concluir abre o registro da sessão de revisão com 30 min', async () => {
    const fetchMock = stub(review([card('c1', 'Primeira')]))
    renderWithProviders(<ReviewSession reviewId="r1" />)
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'Concluir revisão' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([u, i]) => String(u).includes('/complete') && i?.method === 'POST')).toBe(true))
    expect(await screen.findByLabelText('Minutos')).toHaveValue(30)
    expect(screen.getByLabelText('Atividade')).toHaveValue('review')
    expect(screen.getByLabelText(/Tópico/)).toHaveValue('C02.01')
  })

  it('sem cartões aprovados mostra o convite e ainda permite concluir', async () => {
    stub(review([]))
    renderWithProviders(<ReviewSession reviewId="r1" />)
    expect(await screen.findByText('Este tópico ainda não tem cartões aprovados.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Gerar cartões' })).toHaveAttribute('href', '/cartoes')
    expect(screen.getByRole('button', { name: 'Concluir revisão' })).toBeEnabled()
  })
})
