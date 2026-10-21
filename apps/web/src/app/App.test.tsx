import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { renderWithProviders, stubFetch } from '../test/render'
import { App } from './App'

afterEach(() => vi.unstubAllGlobals())

describe('navegação principal', () => {
  it('usa alvos de toque e rótulos legíveis no celular', () => {
    stubFetch([])
    renderWithProviders(<App />)
    const links = within(screen.getByRole('navigation', { name: 'Principal' })).getAllByRole('link')
    expect(links).toHaveLength(7)
    expect(screen.getByRole('link', { name: 'Revisões' })).toHaveAttribute('href', '/revisoes')
    expect(screen.getByRole('link', { name: 'Cartões' })).toHaveAttribute('href', '/cartoes')
    for (const link of links) {
      expect(link).toHaveClass('touch-target', 'text-sm')
      expect(link).not.toHaveClass('text-xs')
    }
  })

  it('no celular, Config. sai da barra inferior e fica como engrenagem no topo', async () => {
    stubFetch([{ match: '/game/summary', body: {
      level: 5, title: 'Analista', xp_total: 1380, xp_into_level: 80, xp_for_next: 100, days_to_exam: 53,
      streak: { current: 1, best: 3, freezes_available: 0 },
    } }])
    renderWithProviders(<App />)
    const nav = screen.getByRole('navigation', { name: 'Principal' })
    expect(within(nav).getByRole('link', { name: 'Config.' })).toHaveClass('max-md:hidden')
    const gear = await screen.findByRole('link', { name: 'Configurações' })
    expect(gear).toHaveAttribute('href', '/config')
    expect(gear).toHaveClass('md:hidden', 'touch-target')
  })

  it('no celular, "Mais" reúne Cartões e Progresso', async () => {
    stubFetch([])
    renderWithProviders(<App />)
    const nav = screen.getByRole('navigation', { name: 'Principal' })
    for (const name of ['Cartões', 'Progresso', 'Config.']) {
      expect(within(nav).getByRole('link', { name })).toHaveClass('max-md:hidden')
    }
    const more = within(nav).getByRole('button', { name: 'Mais' })
    expect(more).toHaveClass('md:hidden')
    await userEvent.setup().click(more)
    const menu = screen.getByRole('menu', { name: 'Mais' })
    expect(within(menu).getByRole('menuitem', { name: 'Cartões' })).toHaveAttribute('href', '/cartoes')
    expect(within(menu).getByRole('menuitem', { name: 'Progresso' })).toHaveAttribute('href', '/progresso')
  })
})
