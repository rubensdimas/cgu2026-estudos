import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { errorBody, summary } from '../../test/fixtures'
import { renderWithProviders, stubFetch } from '../../test/render'
import { ProgressPage } from './ProgressPage'

afterEach(() => vi.unstubAllGlobals())

describe('ProgressPage', () => {
  it('oferece nova tentativa e não busca consultas dependentes quando o resumo falha', async () => {
    const fetchMock = stubFetch([
      { match: '/game/summary', body: errorBody('Erro inesperado.'), status: 500 },
      { match: '/game/config', body: { levels: [], holiday_suggestions: [] } },
    ])
    renderWithProviders(<ProgressPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar o Progresso')
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
    const urls = fetchMock.mock.calls.map(([url]) => String(url))
    expect(urls.some((u) => u.includes('/game/calendar') || u.includes('/game/xp'))).toBe(false)
  })

  it('não mostra gráficos parciais quando o histórico de XP falha', async () => {
    stubFetch([
      { match: '/game/summary', body: summary },
      { match: '/game/calendar', body: { active_days: [], frozen_days: [], neutral_days: [] } },
      { match: '/game/xp', body: errorBody('Erro inesperado.'), status: 500 },
      { match: '/game/config', body: { levels: [], holiday_suggestions: [] } },
    ])
    renderWithProviders(<ProgressPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar o Progresso')
    expect(screen.queryByText('XP acumulado')).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Progresso' })).not.toBeInTheDocument()
  })
})
