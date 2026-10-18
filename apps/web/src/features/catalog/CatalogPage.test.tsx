import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Subject } from '../../shared/api/types'
import { errorBody } from '../../test/fixtures'
import { renderWithProviders, stubFetch } from '../../test/render'
import { CatalogPage } from './CatalogPage'

const REF = '15.2.2 / Estado, democracia, direitos e ciência política'

const subjects = (version = 3): { items: Subject[]; total: number } => ({
  items: [{
    id: 'B01', paper: 'P1', title: 'Estado e democracia', source_ref: REF,
    topics: [
      { id: 'B01.01', title: 'Estado e sociedade', source_ref: `${REF} / tópico 1`,
        progress: { status: 'in_progress', declared_on: '2026-10-10', version } },
      { id: 'B01.02', title: 'Democracia', source_ref: `${REF} / tópico 2`, progress: null },
    ],
  }],
  total: 1,
})

const examVersion = {
  id: 'ev1', title: 'Edital nº 1/2026', publication_date: '2026-09-30', source_url: 'https://example.org/edital.pdf',
  source_sha256: 'abc', exam_date: '2026-12-13', scoring_rules: {},
}

afterEach(() => vi.unstubAllGlobals())

const row = (id: string) => screen.getByRole('combobox', { name: `Estado de ${id}` }).closest('li')!

describe('CatalogPage', () => {
  it('mostra a versão vigente do edital e as referências de origem', async () => {
    stubFetch([{ match: '/exam-versions/current', body: examVersion }, { match: '/subjects', body: subjects() }])
    renderWithProviders(<CatalogPage />)
    const link = await screen.findByRole('link', { name: 'Edital nº 1/2026' })
    expect(link).toHaveAttribute('href', 'https://example.org/edital.pdf')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(screen.getByText(/publicado em 30\/09\/2026/)).toBeInTheDocument()
    expect(screen.getByText(`Item ${REF}`)).toBeInTheDocument()
    expect(within(row('B01.01')).getByText('tópico 1')).toBeInTheDocument()
  })

  it('continua utilizável quando a versão do edital não carrega', async () => {
    stubFetch([
      { match: '/exam-versions/current', body: errorBody('Versão do edital não carregada.', 'not_found'), status: 404 },
      { match: '/subjects', body: subjects() },
    ])
    renderWithProviders(<CatalogPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar a versão do edital')
    expect(screen.getByRole('combobox', { name: 'Estado de B01.01' })).toBeEnabled()
  })

  it('oferece nova tentativa quando o catálogo não carrega', async () => {
    stubFetch([{ match: '/subjects', body: errorBody('Erro inesperado.'), status: 500 }])
    renderWithProviders(<CatalogPage />)
    await waitFor(() => expect(screen.getAllByRole('alert').some((a) =>
      a.textContent?.includes('Não foi possível carregar o Edital'))).toBe(true))
  })

  it('mostra salvando e depois salvo apenas no tópico alterado', async () => {
    let release: (r: Response) => void = () => {}
    const routes = stubFetch([{ match: '/exam-versions/current', body: examVersion }, { match: '/subjects', body: subjects() }])
    const base = routes.getMockImplementation()!
    routes.mockImplementation(async (url: string, init?: RequestInit) =>
      init?.method === 'PUT' ? new Promise<Response>((r) => { release = r }) : base(url, init))
    renderWithProviders(<CatalogPage />)
    const user = userEvent.setup()
    await user.selectOptions(await screen.findByRole('combobox', { name: 'Estado de B01.01' }), 'reviewed')

    const select = screen.getByRole('combobox', { name: 'Estado de B01.01' })
    expect(select).toBeDisabled()
    expect(select).toHaveValue('reviewed')
    expect(within(row('B01.01')).getByText('Salvando…')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Estado de B01.02' })).toBeEnabled()

    release(new Response(JSON.stringify({ topic_id: 'B01.01', status: 'reviewed', declared_on: '2026-10-14', version: 4 })))
    expect(await within(row('B01.01')).findByText('Salvo')).toBeInTheDocument()
    expect(select).toBeEnabled()
    expect(select).toHaveValue('reviewed')
    expect(within(row('B01.02')).queryByText('Salvo')).not.toBeInTheDocument()
  })

  it('mantém o valor confirmado e mostra o erro no tópico quando a gravação falha', async () => {
    stubFetch([
      { match: '/exam-versions/current', body: examVersion },
      { match: '/subjects', body: subjects() },
      { method: 'PUT', match: '/topics/B01.01/progress', body: errorBody('Erro inesperado.'), status: 500 },
    ])
    renderWithProviders(<CatalogPage />)
    await userEvent.setup().selectOptions(await screen.findByRole('combobox', { name: 'Estado de B01.01' }), 'reviewed')
    expect(await within(row('B01.01')).findByRole('alert')).toHaveTextContent('Erro inesperado.')
    expect(screen.getByRole('combobox', { name: 'Estado de B01.01' })).toHaveValue('in_progress')
    expect(within(row('B01.01')).queryByText('Salvo')).not.toBeInTheDocument()
  })

  it('recarrega a versão e avisa quando o tópico foi alterado em outro lugar', async () => {
    const subjectsRoute = { match: '/subjects', body: subjects(3) as unknown }
    const putRoute = { method: 'PUT', match: '/topics/B01.01/progress', status: 409,
      body: errorBody('Este registro foi alterado. Recarregue antes de editar.', 'version_conflict') as unknown }
    const fetchMock = stubFetch([{ match: '/exam-versions/current', body: examVersion }, subjectsRoute, putRoute])
    renderWithProviders(<CatalogPage />)
    const user = userEvent.setup()
    const select = await screen.findByRole('combobox', { name: 'Estado de B01.01' })
    subjectsRoute.body = subjects(4)
    await user.selectOptions(select, 'reviewed')

    expect(await within(row('B01.01')).findByRole('alert')).toHaveTextContent('Alterado em outro lugar')
    await waitFor(() => expect(fetchMock.mock.calls.filter(([u]) => String(u).includes('/subjects')).length).toBe(2))

    Object.assign(putRoute, { status: 200, body: { topic_id: 'B01.01', status: 'first_pass', declared_on: '2026-10-14', version: 5 } })
    await user.selectOptions(screen.getByRole('combobox', { name: 'Estado de B01.01' }), 'first_pass')
    await waitFor(() => expect(fetchMock.mock.calls.filter(([, i]) => i?.method === 'PUT').length).toBe(2))
    const last = fetchMock.mock.calls.filter(([, i]) => i?.method === 'PUT')[1]
    expect(JSON.parse(last[1]!.body as string)).toEqual({ status: 'first_pass', version: 4 })
  })
})
