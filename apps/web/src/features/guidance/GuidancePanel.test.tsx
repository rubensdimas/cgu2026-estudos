import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Guidance, Occurrence } from '../../shared/api/types'
import { renderWithProviders, stubFetch } from '../../test/render'
import { GuidancePanel } from './GuidancePanel'

const occ: Occurrence = {
  id: 'o1', version: 5, week_start: '2026-10-05', planned_on: '2026-10-11', window: 'middle', status: 'pending',
  skip_reason: null, actual_minutes: 0, completed_on: null, suggested_topic_id: null, essay_kind: null,
  slot: { code: 'S14', title: 'Discursiva de complementares', purpose: 'essay', activity: 'essay', minutes: 60,
    selection_mode: 'complementary', candidate_topic_ids: [] },
}

const essay: Guidance = {
  roteiro: { ate: null, titulo: 'Discursiva de complementares (Q1)', passos: [{ minutos: 10, texto: 'Monte o esquema.' }] },
  nota: null, topic: null, materiais: [], next_theme_id: 'D2', lembretes: ['Até 30 linhas: o que passar do limite não é corrigido.'],
  tema: { id: 'D1', titulo: 'Transparência ativa', topic_ids: ['C02.01'], linhas: 30, texto_motivador: 'A LAI…',
    comando: 'Redija um texto dissertativo abordando:', aspectos: [{ texto: 'conceito de transparência ativa', valor: 10 }],
    espelho: { texto_padrao: 'Espera-se que…', quesitos: [{ id: '2.1', texto: 'Conceito', conceitos: ['Conceito 0 – não abordou'] }] },
    fontes: [{ titulo: 'Lei 12.527/2011', url: 'https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm' }],
    semelhante_a: null },
}

afterEach(() => vi.unstubAllGlobals())

describe('GuidancePanel', () => {
  it('só busca ao abrir e esconde o espelho até pedir', async () => {
    const fetchMock = stubFetch([{ match: '/occurrences/o1/guidance', body: essay }])
    renderWithProviders(<GuidancePanel occ={occ} />)
    expect(fetchMock).not.toHaveBeenCalled()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Como fazer este bloco' }))
    expect(await screen.findByText('Transparência ativa')).toBeInTheDocument()
    expect(screen.getByText(/\[valor: 10,00 pontos\]/)).toBeInTheDocument()
    expect(screen.getByText(/o que passar do limite/)).toBeInTheDocument()
    expect(screen.queryByText('Espera-se que…')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Ver pontos esperados' }))
    expect(screen.getByText('Espera-se que…')).toBeInTheDocument()
  })

  it('troca o tema com a versão do bloco', async () => {
    const fetchMock = stubFetch([{ match: '/occurrences/o1/guidance', body: essay },
      { method: 'PATCH', match: '/occurrences/o1', body: { game_delta: null } }])
    renderWithProviders(<GuidancePanel occ={occ} />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Como fazer este bloco' }))
    await user.click(await screen.findByRole('button', { name: 'Trocar tema' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(true))
    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')!
    expect(JSON.parse(patch[1]!.body as string)).toEqual({ version: 5, theme_id: 'D2' })
  })

  it('omite seções vazias', async () => {
    const plain: Guidance = { ...essay, tema: null, next_theme_id: null, lembretes: [],
      topic: { id: 'C04.01', title: 'Perguntas e fontes', subitens: [] } }
    stubFetch([{ match: '/occurrences/o1/guidance', body: plain }])
    renderWithProviders(<GuidancePanel occ={occ} />)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Como fazer este bloco' }))
    expect(await screen.findByText(/Perguntas e fontes/)).toBeInTheDocument()
    expect(screen.queryByText('Materiais')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Trocar tema' })).not.toBeInTheDocument()
    expect(screen.queryByText('Regras do edital')).not.toBeInTheDocument()
  })
})
