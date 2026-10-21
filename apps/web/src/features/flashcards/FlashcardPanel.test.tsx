import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Flashcard, Session } from '../../shared/api/types'
import { FlashcardPanel } from './FlashcardPanel'

const session: Session = {
  id: 's1', version: 1, occurrence_id: null, studied_on: '2026-10-09', duration_minutes: 50, activity: 'theory',
  essay_kind: null, topic_ids: ['C02.01'], notes: 'LAI',
}

const card: Flashcard = {
  id: 'c1', version: 1, session_id: 's1', topic_id: 'C02.01', subitem: '1.2', category: 'distincao',
  front: 'Qual a diferença entre sigilo e informação pessoal?', back: 'Sigilo protege o Estado; informação pessoal, o titular.',
  status: 'draft',
}

const batch = { model: 'm', studied: 'LAI', origin: 'observação da sessão', focus: 'sigilos', priorities: [], created_at: '' }
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status })

type Route = (url: string, init?: RequestInit) => Response | undefined

function stub(route: Route, enabled = true) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const hit = route(url, init)
    if (hit) return hit
    if (url.endsWith('/flashcards/status')) return json({ enabled, model: 'm' })
    if (url.endsWith('/sessions/s1/flashcards')) return json({ batch: null, cards: [] })
    throw new Error(`rota inesperada ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(<QueryClientProvider client={qc}><FlashcardPanel session={session} /></QueryClientProvider>)
}

const posts = (m: ReturnType<typeof stub>, suffix: string) =>
  m.mock.calls.filter(([u, i]) => String(u).endsWith(suffix) && i?.method === 'POST')

afterEach(() => vi.unstubAllGlobals())

describe('FlashcardPanel', () => {
  it('gera com o texto informado e mostra os rascunhos com subitem', async () => {
    let generated = false
    const fetchMock = stub((url, init) => {
      if (!url.endsWith('/sessions/s1/flashcards')) return undefined
      if (init?.method === 'POST') generated = true
      return generated ? json({ batch, cards: [card] }, init?.method === 'POST' ? 201 : 200) : undefined
    })
    renderPanel()
    const user = userEvent.setup()
    const field = await screen.findByLabelText('O que estudei / errei')
    expect(field).toHaveValue('LAI')
    await user.type(field, ' e sigilo')
    await user.click(await screen.findByRole('button', { name: 'Gerar flashcards' }))
    expect(await screen.findByText(card.front)).toBeInTheDocument()
    expect(screen.getByText(card.back)).toBeInTheDocument()
    expect(screen.getByText('Subitem 1.2')).toBeInTheDocument()
    expect(JSON.parse(posts(fetchMock, '/sessions/s1/flashcards')[0][1]!.body as string)).toEqual({ studied: 'LAI e sigilo' })
  })

  it('desabilita a geração sem chave', async () => {
    stub(() => undefined, false)
    renderPanel()
    expect(await screen.findByText('Configure OPENAI_API_KEY no .env para gerar flashcards.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Gerar flashcards' })).toBeDisabled()
  })

  it('mostra erro e permite tentar de novo', async () => {
    const error = { error: { code: 'ai_failed', message: 'Não foi possível gerar agora. Tente novamente.', fields: {} } }
    const fetchMock = stub((url, init) =>
      init?.method === 'POST' && url.endsWith('/sessions/s1/flashcards') ? json(error, 502) : undefined)
    renderPanel()
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'Gerar flashcards' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível gerar agora. Tente novamente.')
    await user.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(posts(fetchMock, '/sessions/s1/flashcards')).toHaveLength(2))
  })

  it('aprovar todos envia a ação da sessão', async () => {
    const fetchMock = stub((url, init) => {
      if (url.endsWith('/sessions/s1/flashcards') && init?.method === 'GET') return json({ batch, cards: [card] })
      if (url.endsWith('/flashcards/approve')) return json({ batch, cards: [{ ...card, status: 'approved' }] })
    })
    renderPanel()
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Aprovar todos' }))
    await waitFor(() => expect(posts(fetchMock, '/sessions/s1/flashcards/approve')).toHaveLength(1))
  })
})
