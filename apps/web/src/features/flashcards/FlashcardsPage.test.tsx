import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Flashcard, Session } from '../../shared/api/types'
import { renderWithProviders, stubFetch } from '../../test/render'
import { FlashcardsPage } from './FlashcardsPage'

const session = (id: string, topic: string): Session => ({
  id, version: 1, occurrence_id: null, studied_on: '2026-10-08', duration_minutes: 60, activity: 'theory',
  essay_kind: null, topic_ids: [topic], notes: '',
})

const card: Flashcard = {
  id: 'c1', version: 2, session_id: 's1', topic_id: 'C02.01', subitem: '1.1', category: 'conceito',
  front: 'O que é transparência ativa?', back: 'Divulgação de ofício, sem pedido.', status: 'approved',
}

const subjects = [{ id: 'C02', paper: 'P2', title: 'Transparência', source_ref: '', topics: [
  { id: 'C02.01', title: 'Acesso à informação', source_ref: '', progress: null },
  { id: 'C03.01', title: 'Direito público', source_ref: '', progress: null },
] }]

function stub() {
  stubFetch([
    { match: '/game/summary', body: { today: '2026-10-09' } },
    { match: '/subjects', body: { items: subjects, total: 1 } },
    { match: '/flashcards/sessions', body: { total: 2, items: [
      { session: session('s1', 'C02.01'), drafts: 0, approved: 2, generated: true },
      { session: session('s2', 'C03.01'), drafts: 0, approved: 0, generated: false },
    ] } },
    { match: '/flashcards', body: { items: [card], total: 1 } },
  ])
}

afterEach(() => vi.unstubAllGlobals())

describe('FlashcardsPage', () => {
  it('lista sessões de teoria com o estado dos cartões', async () => {
    stub()
    renderWithProviders(<FlashcardsPage />)
    expect(await screen.findByText('2 aprovados')).toBeInTheDocument()
    expect(screen.getByText('Sem cartões')).toBeInTheDocument()
  })

  it('agrupa o baralho por tópico e revela o verso', async () => {
    stub()
    renderWithProviders(<FlashcardsPage />)
    const user = userEvent.setup()
    await user.click(await screen.findByText(/C02\.01 Acesso à informação/, { selector: 'summary *' }))
    expect(screen.getByText(card.front)).toBeInTheDocument()
    expect(screen.queryByText(card.back)).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Mostrar verso' }))
    expect(screen.getByText(card.back)).toBeInTheDocument()
  })
})
