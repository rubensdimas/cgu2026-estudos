import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { errorBody } from '../../test/fixtures'
import { renderWithProviders, stubFetch } from '../../test/render'
import { SettingsPage } from './SettingsPage'

afterEach(() => vi.unstubAllGlobals())

describe('SettingsPage', () => {
  it('mantém o formulário e oferece nova tentativa quando as folgas não carregam', async () => {
    stubFetch([{ match: '/day-offs', body: errorBody('Erro inesperado.'), status: 500 }])
    renderWithProviders(<SettingsPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar as folgas')
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Marcar folga' })).toBeEnabled()
  })
})
