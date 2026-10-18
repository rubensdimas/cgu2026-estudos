import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { DayView, Occurrence } from '../../shared/api/types'
import { errorBody, summary } from '../../test/fixtures'
import { renderWithProviders, stubFetch } from '../../test/render'
import { OpenDayCard, TodayPage, TodaySessions } from './TodayPage'

const pending = (id: string, title: string, planned_on: string): Occurrence => ({
  id, version: 1, week_start: '2026-10-05', planned_on, window: 'before', status: 'pending', skip_reason: null,
  actual_minutes: 0, completed_on: null, suggested_topic_id: null,
  slot: { code: 'S13', title, purpose: 'complementary', activity: 'theory', minutes: 60,
    selection_mode: 'alternate_subjects', candidate_topic_ids: [] },
})

const saturday: DayView = {
  date: '2026-10-10', kind: 'free', in_plan: true, week_generated: true, occurrences: [], mission: null, xp_today: 0,
}

afterEach(() => vi.unstubAllGlobals())

describe('OpenDayCard no fim de semana', () => {
  it('envia os blocos pendentes escolhidos para a missão livre', async () => {
    const fetchMock = stubFetch([
      { match: '/occurrences?from=2026-10-05&to=2026-10-11',
        body: { items: [pending('a', 'Complementares e revisão', '2026-10-09'), pending('b', 'Situação-problema de TI', '2026-10-09')], total: 2 } },
      { method: 'POST', match: '/days/2026-10-10/mission', body: { id: 'm', items: [], game_delta: { xp_gained: 0, entries: [], level_up: null, mission_complete: [], streak: 0 } }, status: 201 },
    ])
    renderWithProviders(<OpenDayCard view={saturday} />)
    const user = userEvent.setup()
    const open = screen.getByRole('button', { name: 'Abrir missão livre' })
    expect(open).toBeDisabled()
    await user.click(await screen.findByLabelText(/Situação-problema de TI/))
    await user.click(open)
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(true))
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')!
    expect(JSON.parse(post[1]!.body as string)).toEqual({ occurrence_ids: ['b'] })
  })
})

describe('TodaySessions', () => {
  it('exclui uma sessão do dia após confirmação', async () => {
    const fetchMock = stubFetch([
      { match: '/sessions?from=2026-10-09&to=2026-10-09',
        body: { items: [{ id: 's1', version: 1, occurrence_id: null, studied_on: '2026-10-09', duration_minutes: 600,
          activity: 'theory', essay_kind: null, topic_ids: ['E01.02'], notes: '' }], total: 1 } },
      { method: 'DELETE', match: '/sessions/s1', body: null, status: 204 },
    ])
    vi.stubGlobal('confirm', vi.fn(() => true))
    renderWithProviders(<TodaySessions day="2026-10-09" />)
    await userEvent.setup().click(await screen.findByRole('button', { name: /Excluir sessão de 600 min/ }))
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith('/api/v1/sessions/s1', expect.objectContaining({ method: 'DELETE' })))
  })
})

describe('estados de falha em Hoje', () => {
  it('oferece nova tentativa quando o resumo não carrega', async () => {
    stubFetch([{ match: '/game/summary', body: errorBody('Erro inesperado.'), status: 500 }])
    renderWithProviders(<TodayPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar o dia')
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
  })

  it('oferece nova tentativa quando o dia não carrega', async () => {
    stubFetch([
      { match: '/game/summary', body: summary },
      { match: '/days/2026-10-14', body: errorBody('Erro inesperado.'), status: 500 },
    ])
    renderWithProviders(<TodayPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar o dia')
  })

  it('não esconde a lista de sessões quando ela falha', async () => {
    stubFetch([{ match: '/sessions?', body: errorBody('Erro inesperado.'), status: 500 }])
    renderWithProviders(<TodaySessions day="2026-10-09" />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar as sessões de hoje')
  })

  it('não apresenta semana sem blocos quando a busca de blocos falha', async () => {
    stubFetch([{ match: '/occurrences?', body: errorBody('Erro inesperado.'), status: 500 }])
    renderWithProviders(<OpenDayCard view={saturday} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar os blocos da semana')
    expect(screen.queryByText(/Nenhum bloco pendente/)).not.toBeInTheDocument()
  })
})
