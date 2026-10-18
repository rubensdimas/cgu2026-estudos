import { fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Occurrence } from '../../shared/api/types'
import { errorBody, summary } from '../../test/fixtures'
import { renderWithProviders, stubFetch } from '../../test/render'
import { CyclePage, OccurrenceRow } from './CyclePage'

const occ: Occurrence = {
  id: 'occ-1', version: 3, week_start: '2026-10-12', planned_on: '2026-10-12', window: 'before', status: 'pending',
  skip_reason: null, actual_minutes: 0, completed_on: null, suggested_topic_id: 'B01.01',
  slot: { code: 'S01', title: 'Estado e sociedade', purpose: 'basic', activity: 'theory', minutes: 60,
    selection_mode: 'alternate_subjects', candidate_topic_ids: ['B01.01'] },
}

afterEach(() => vi.unstubAllGlobals())

describe('OccurrenceRow', () => {
  it('não dispensa o bloco quando o usuário cancela o motivo', async () => {
    const fetchMock = stubFetch([])
    vi.stubGlobal('prompt', vi.fn(() => null))
    renderWithProviders(<ul><OccurrenceRow occ={occ} /></ul>)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Dispensar' }))
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

const patches = (fetchMock: ReturnType<typeof stubFetch>) => fetchMock.mock.calls.filter(([, i]) => i?.method === 'PATCH')

async function openMove() {
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Remanejar bloco' }))
  fireEvent.change(screen.getByLabelText('Data'), { target: { value: '2026-10-14' } })
  await user.selectOptions(screen.getByLabelText('Janela'), 'after')
  return user
}

describe('remanejamento', () => {
  it('mostra o destino e só envia após confirmar', async () => {
    const fetchMock = stubFetch([{ method: 'PATCH', match: '/occurrences/occ-1', body: { ...occ, game_delta: null } }])
    renderWithProviders(<ul><OccurrenceRow occ={occ} /></ul>)
    const user = await openMove()
    expect(screen.getByText(/Mover de seg\.?, 12\/10, Antes, para qua\.?, 14\/10, Depois\./)).toBeInTheDocument()
    expect(patches(fetchMock)).toHaveLength(0)
    await user.click(screen.getByRole('button', { name: 'Confirmar remanejamento' }))
    await waitFor(() => expect(patches(fetchMock)).toHaveLength(1))
    const [url, init] = patches(fetchMock)[0]
    expect(url).toBe('/api/v1/occurrences/occ-1')
    expect(JSON.parse(init!.body as string)).toEqual({ version: 3, planned_on: '2026-10-14', window: 'after' })
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Confirmar remanejamento' })).not.toBeInTheDocument())
  })

  it('não permite confirmar quando o destino é igual à origem', async () => {
    stubFetch([])
    renderWithProviders(<ul><OccurrenceRow occ={occ} /></ul>)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Remanejar bloco' }))
    expect(screen.getByRole('button', { name: 'Confirmar remanejamento' })).toBeDisabled()
  })

  it('cancelar descarta o rascunho', async () => {
    const fetchMock = stubFetch([])
    renderWithProviders(<ul><OccurrenceRow occ={occ} /></ul>)
    const user = await openMove()
    await user.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(screen.queryByLabelText('Data')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Remanejar bloco' }))
    expect(screen.getByLabelText('Data')).toHaveValue('2026-10-12')
    expect(screen.getByLabelText('Janela')).toHaveValue('before')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('mantém o rascunho aberto após erro do servidor', async () => {
    stubFetch([{ method: 'PATCH', match: '/occurrences/occ-1', body: errorBody('Erro inesperado.'), status: 500 }])
    renderWithProviders(<ul><OccurrenceRow occ={occ} /></ul>)
    const user = await openMove()
    await user.click(screen.getByRole('button', { name: 'Confirmar remanejamento' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Erro inesperado.')
    expect(screen.getByLabelText('Data')).toHaveValue('2026-10-14')
    expect(screen.getByLabelText('Janela')).toHaveValue('after')
    expect(screen.getByRole('button', { name: 'Confirmar remanejamento' })).toBeEnabled()
  })

  it('recarrega a semana e mantém o rascunho quando o bloco foi alterado em outro lugar', async () => {
    const fetchMock = stubFetch([
      { match: '/game/summary', body: summary },
      { match: '/occurrences?', body: { items: [occ], total: 1 } },
      { method: 'PATCH', match: '/occurrences/occ-1', status: 409,
        body: errorBody('Este registro foi alterado. Recarregue antes de editar.', 'version_conflict') },
    ])
    renderWithProviders(<CyclePage />)
    await screen.findByRole('button', { name: 'Remanejar bloco' })
    const user = await openMove()
    await user.click(screen.getByRole('button', { name: 'Confirmar remanejamento' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Alterado em outro lugar')
    await waitFor(() => expect(fetchMock.mock.calls.filter(([u]) => String(u).includes('/occurrences?')).length).toBe(2))
    expect(screen.getByLabelText('Data')).toHaveValue('2026-10-14')
  })
})

describe('CyclePage', () => {
  it('oferece nova tentativa em vez de semana não gerada quando a busca da semana falha', async () => {
    stubFetch([
      { match: '/game/summary', body: summary },
      { match: '/occurrences?', body: errorBody('Erro inesperado.'), status: 500 },
    ])
    renderWithProviders(<CyclePage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar a semana')
    expect(screen.queryByText('Semana ainda não gerada.')).not.toBeInTheDocument()
  })
})
