import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Occurrence, Subject } from '../../shared/api/types'
import { GameToastProvider } from '../../shared/ui/GameToast'
import { SessionForm, type SubjectsQuery } from './SessionForm'

const subjects: Subject[] = [
  { id: 'C02', paper: 'P2', title: 'Transparência', source_ref: '', topics: [{ id: 'C02.01', title: 'Acesso à informação', source_ref: '', progress: null }] },
]

const occurrence: Occurrence = {
  id: 'occ-1', version: 1, week_start: '2026-10-05', planned_on: '2026-10-09', window: 'before', status: 'pending',
  skip_reason: null, actual_minutes: 0, completed_on: null, suggested_topic_id: 'C02.01',
  slot: { code: 'S13', title: 'Complementares e revisão', purpose: 'complementary', activity: 'theory', minutes: 60,
    selection_mode: 'alternate_subjects', candidate_topic_ids: ['C02.01'] },
}

const query = { isPending: false, isFetching: false, error: null, refetch: () => {} }
const loaded = { ...query, data: { items: subjects, total: 1 } }

function renderForm(onSaved = vi.fn(), topics: SubjectsQuery = loaded) {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  const tree = (t: SubjectsQuery) => (
    <QueryClientProvider client={qc}>
      <GameToastProvider>
        <SessionForm occurrence={occurrence} today="2026-10-09" subjects={t} onSaved={onSaved} onCancel={vi.fn()} />
      </GameToastProvider>
    </QueryClientProvider>
  )
  const { rerender } = render(tree(topics))
  return { onSaved, rerender: (t: SubjectsQuery) => rerender(tree(t)) }
}

afterEach(() => vi.unstubAllGlobals())

describe('SessionForm', () => {
  it('mantém os dados após falha de rede e reenvia com o mesmo id', async () => {
    const delta = { xp_gained: 80, entries: [], level_up: null, mission_complete: [], streak: 1 }
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(new Response(JSON.stringify({ game_delta: delta }), { status: 201 }))
    vi.stubGlobal('fetch', fetchMock)
    const { onSaved } = renderForm()
    const user = userEvent.setup()

    const minutes = screen.getByLabelText('Minutos')
    await user.clear(minutes)
    await user.type(minutes, '45')
    await user.click(screen.getByRole('button', { name: 'Registrar sessão' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Sem conexão')
    expect(screen.getByLabelText('Minutos')).toHaveValue(45)
    expect(onSaved).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Registrar sessão' }))
    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    const [first, second] = fetchMock.mock.calls.map((c) => JSON.parse(c[1].body))
    expect(second.id).toBe(first.id)
    expect(second).toMatchObject({ duration_minutes: 45, topic_ids: ['C02.01'], complete_occurrence: true, occurrence_id: 'occ-1' })
  })

  it('mostra erros de campo do servidor', async () => {
    const body = { error: { code: 'invalid_input', message: 'Revise os campos destacados.', fields: { studied_on: 'Data futura.' } } }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 422 })))
    renderForm()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Registrar sessão' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('studied_on: Data futura.')
  })

  it('mantém o rascunho quando os tópicos não carregam e os oferece após nova tentativa', async () => {
    const failed = { ...query, isPending: true, error: new Error('Erro inesperado.') }
    const { rerender } = renderForm(vi.fn(), failed)
    expect(screen.getByRole('alert')).toHaveTextContent('Não foi possível carregar os tópicos')
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: /Tópico/ })).not.toBeInTheDocument()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Observação'), 'lei 12.527')
    rerender(loaded)
    expect(screen.getByLabelText('Observação')).toHaveValue('lei 12.527')
    expect(screen.getByRole('option', { name: 'C02.01 Acesso à informação' })).toBeInTheDocument()
  })
})
