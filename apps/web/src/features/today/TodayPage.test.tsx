import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { DayView, MissionItem, Occurrence } from '../../shared/api/types'
import { errorBody, summary } from '../../test/fixtures'
import { renderWithProviders, stubFetch } from '../../test/render'
import { CheckoutRow, HolidayBanner, MissionRow, OpenDayCard, TodayPage, TodaySessions } from './TodayPage'

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
    expect(JSON.parse(post[1]!.body as string)).toEqual({ occurrence_ids: ['b'], review_ids: [] })
  })

  it('pré-marca até 4 revisões vencidas e permite abrir só com elas', async () => {
    const due = ['r1', 'r2', 'r3', 'r4', 'r5'].map((id, i) => ({
      id, version: 1, session_id: 's', topic_id: `C0${i + 1}.01`, offset_days: 1, due_on: `2026-10-0${i + 1}`,
      status: 'pending', completed_on: null, late: true, cards_count: 0,
    }))
    const fetchMock = stubFetch([
      { match: '/occurrences?from=2026-10-05&to=2026-10-11', body: { items: [], total: 0 } },
      { match: '/reviews/due?day=2026-10-10', body: { items: due, total: 5 } },
      { match: '/subjects', body: { items: [], total: 0 } },
      { method: 'POST', match: '/days/2026-10-10/mission', body: { id: 'm', items: [], game_delta: { xp_gained: 0, entries: [], level_up: null, mission_complete: [], streak: 0 } }, status: 201 },
    ])
    renderWithProviders(<OpenDayCard view={saturday} />)
    const user = userEvent.setup()
    expect(await screen.findByLabelText(/C05\.01/)).not.toBeChecked()
    expect(screen.getByLabelText(/C01\.01/)).toBeChecked()
    await user.click(screen.getByRole('button', { name: 'Abrir missão livre' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(true))
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')!
    expect(JSON.parse(post[1]!.body as string)).toEqual({ occurrence_ids: [], review_ids: ['r1', 'r2', 'r3', 'r4'] })
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
    stubFetch([
      { match: '/occurrences?', body: errorBody('Erro inesperado.'), status: 500 },
      { match: '/reviews/due', body: { items: [], total: 0 } },
    ])
    renderWithProviders(<OpenDayCard view={saturday} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar os blocos da semana')
    expect(screen.queryByText(/Nenhum bloco pendente/)).not.toBeInTheDocument()
  })
})

describe('gravações com falha visível', () => {
  const checkout: MissionItem = { id: 'i9', position: 9, kind: 'checkout', ref_id: null, required: false, target: null,
    state: 'pending', na_reason: null }

  it('mantém o texto do check-out e mostra o erro quando salvar falha', async () => {
    stubFetch([{ method: 'PUT', match: '/missions/m1/checkout', body: errorBody('Erro inesperado.'), status: 500 }])
    renderWithProviders(<ul><CheckoutRow missionId="m1" item={checkout} note={null} /></ul>)
    const user = userEvent.setup()
    await user.type(screen.getByRole('textbox'), 'juros compostos')
    await user.click(screen.getByRole('button', { name: 'Salvar check-out' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Erro inesperado.')
    expect(screen.getByRole('textbox')).toHaveValue('juros compostos')
  })

  it('mostra o erro quando marcar "não se aplica" falha', async () => {
    const occ = pending('o1', 'Estado e sociedade', '2026-10-14')
    const item: MissionItem = { id: 'i1', position: 1, kind: 'block', ref_id: 'o1', required: true, target: null,
      state: 'pending', na_reason: null }
    const view: DayView = { date: '2026-10-14', kind: 'weekday', in_plan: true, week_generated: true, occurrences: [occ],
      mission: { id: 'm1', date: '2026-10-14', kind: 'weekday', checkout_note: null, complete: false, items: [item] }, xp_today: 0 }
    stubFetch([
      { match: '/plans/current', body: { id: 'p', starts_on: '2026-10-09', ends_on: '2026-12-12', exam_date: '2026-12-13' } },
      { method: 'PATCH', match: '/missions/m1/items/i1', body: errorBody('Erro inesperado.'), status: 500 },
    ])
    renderWithProviders(<ul><MissionRow item={item} missionId="m1" view={view} onRegister={vi.fn()} /></ul>)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Não se aplica hoje' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Erro inesperado.')
  })

  it('mostra o erro quando marcar o feriado como folga falha', async () => {
    stubFetch([
      { match: '/game/summary', body: { ...summary, holiday_suggestion: { date: '2026-10-15', label: 'Dia do Professor' } } },
      { method: 'PUT', match: '/day-offs/2026-10-15', body: errorBody('Erro inesperado.'), status: 500 },
    ])
    renderWithProviders(<HolidayBanner />)
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Marcar folga' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Erro inesperado.')
  })
})
