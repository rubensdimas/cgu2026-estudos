import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Occurrence, OccurrenceStatus } from '../../shared/api/types'
import { renderWithProviders, stubFetch } from '../../test/render'
import { LateBlocks } from './LateBlocks'

const occ = (id: string, title: string, status: OccurrenceStatus = 'pending'): Occurrence => ({
  id, version: 4, week_start: '2026-10-05', planned_on: '2026-10-09', window: 'after', status, skip_reason: null,
  actual_minutes: 0, completed_on: null, suggested_topic_id: null,
  slot: { code: 'S15', title, purpose: 'essay', activity: 'essay', minutes: 60, selection_mode: 'technical_case',
    candidate_topic_ids: [] },
})

const plan = { match: '/plans/current', body: { id: 'p', starts_on: '2026-10-09', ends_on: '2026-12-12', exam_date: '2026-12-13' } }

afterEach(() => vi.unstubAllGlobals())

describe('LateBlocks', () => {
  it('conta só pendentes e traz os escolhidos para hoje', async () => {
    const fetchMock = stubFetch([plan,
      { match: '/occurrences?from=2026-10-09&to=2026-10-11',
        body: { items: [occ('x', 'Situação-problema de TI'), occ('y', 'Dispensado', 'skipped')], total: 2 } },
      { method: 'PATCH', match: '/occurrences/x', body: { game_delta: null } }])
    renderWithProviders(<LateBlocks today="2026-10-12" />)
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: /1 bloco atrasado/ }))
    expect(screen.queryByLabelText(/Dispensado/)).not.toBeInTheDocument()
    const bring = screen.getByRole('button', { name: 'Trazer para hoje' })
    expect(bring).toBeDisabled()
    await user.click(screen.getByLabelText(/Situação-problema de TI/))
    await user.click(bring)
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(true))
    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')!
    expect(JSON.parse(patch[1]!.body as string)).toEqual({ version: 4, planned_on: '2026-10-12' })
  })

  it('não consulta no primeiro dia do plano', async () => {
    const fetchMock = stubFetch([plan, { match: '/occurrences?from=2026-10-09&to=2026-10-11',
      body: { items: [occ('x', 'Controle')], total: 1 } }])
    renderWithProviders(<><LateBlocks today="2026-10-09" /><LateBlocks today="2026-10-12" /></>)
    // O aviso do dia 12 (controle) prova que o plano já carregou.
    expect(await screen.findAllByRole('button', { name: /atrasado/ })).toHaveLength(1)
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('to=2026-10-08'))).toBe(false)
  })
  it('após falha parcial, desmarca só o que já foi trazido', async () => {
    stubFetch([plan,
      { match: '/occurrences?from=2026-10-09&to=2026-10-11',
        body: { items: [occ('x', 'Bloco X'), occ('z', 'Bloco Z')], total: 2 } },
      { method: 'PATCH', match: '/occurrences/x', body: { game_delta: null } },
      { method: 'PATCH', match: '/occurrences/z', body: { error: { code: 'version_conflict', message: 'Este registro foi alterado.' } }, status: 409 }])
    renderWithProviders(<LateBlocks today="2026-10-12" />)
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: /2 blocos atrasados/ }))
    await user.click(screen.getByLabelText(/Bloco X/))
    await user.click(screen.getByLabelText(/Bloco Z/))
    await user.click(screen.getByRole('button', { name: 'Trazer para hoje' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Este registro foi alterado.')
    expect(screen.getByLabelText(/Bloco X/)).not.toBeChecked()
    expect(screen.getByLabelText(/Bloco Z/)).toBeChecked()
  })
})
