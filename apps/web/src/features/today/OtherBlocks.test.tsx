import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { DayView, Occurrence, OccurrenceStatus } from '../../shared/api/types'
import { renderWithProviders, stubFetch } from '../../test/render'
import { MoveTomorrowButton } from './MoveTomorrow'
import { OtherBlocks } from './OtherBlocks'

const occ = (id: string, title: string, status: OccurrenceStatus = 'pending'): Occurrence => ({
  id, version: 2, week_start: '2026-10-05', planned_on: '2026-10-10', window: 'middle', status, skip_reason: null,
  actual_minutes: 0, completed_on: null, suggested_topic_id: null, essay_kind: null,
  slot: { code: 'S14', title, purpose: 'essay', activity: 'essay', minutes: 60, selection_mode: 'complementary',
    candidate_topic_ids: [] },
})

const view = (date: string, occurrences: Occurrence[]): DayView => ({
  date, kind: 'free', in_plan: true, week_generated: true, xp_today: 0, occurrences,
  mission: { id: 'm', date, kind: 'free', checkout_note: null, complete: true, items: [
    { id: 'i1', position: 0, kind: 'block', ref_id: 'a', required: true, target: null, state: 'done', na_reason: null },
  ] },
})

const plan = (ends_on: string) => ({ match: '/plans/current', body: { id: 'p', starts_on: '2026-10-09', ends_on, exam_date: '2026-12-13' } })

afterEach(() => vi.unstubAllGlobals())

describe('OtherBlocks', () => {
  it('não repete bloco da missão e esconde dispensados', async () => {
    stubFetch([plan('2026-12-12')])
    renderWithProviders(<OtherBlocks view={view('2026-10-10', [occ('a', 'Da missão'), occ('b', 'Remanejado'),
      occ('c', 'Dispensado', 'skipped')])} onRegister={() => {}} />)
    expect(screen.getByText(/Remanejado/)).toBeInTheDocument()
    expect(screen.queryByText(/Da missão/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Dispensado/)).not.toBeInTheDocument()
  })

  it('registra sessão e move para amanhã mantendo a janela', async () => {
    const fetchMock = stubFetch([plan('2026-12-12'),
      { method: 'PATCH', match: '/occurrences/b', body: { game_delta: null } }])
    const onRegister = vi.fn()
    renderWithProviders(<OtherBlocks view={view('2026-10-10', [occ('b', 'Remanejado')])} onRegister={onRegister} />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Registrar sessão' }))
    expect(onRegister).toHaveBeenCalledWith(expect.objectContaining({ id: 'b' }))
    await user.click(await screen.findByRole('button', { name: 'Mover para amanhã' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(true))
    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')!
    expect(JSON.parse(patch[1]!.body as string)).toEqual({ version: 2, planned_on: '2026-10-11' })
  })

  it('"Mover para amanhã" some no último dia do plano', async () => {
    stubFetch([plan('2026-12-12')])
    renderWithProviders(<>
      <OtherBlocks view={view('2026-12-12', [occ('b', 'Remanejado')])} onRegister={() => {}} />
      <MoveTomorrowButton occ={occ('z', 'Controle')} today="2026-12-10" />
    </>)
    // O botão de controle (dia 10) prova que o plano já carregou.
    await screen.findByRole('button', { name: 'Mover para amanhã' })
    expect(screen.getAllByRole('button', { name: 'Mover para amanhã' })).toHaveLength(1)
  })

  it('não aparece sem missão aberta', () => {
    stubFetch([plan('2026-12-12')])
    const v = { ...view('2026-10-10', [occ('b', 'Remanejado')]), mission: null }
    renderWithProviders(<OtherBlocks view={v} onRegister={() => {}} />)
    expect(screen.queryByRole('region', { name: 'Outros blocos de hoje' })).not.toBeInTheDocument()
  })
})
