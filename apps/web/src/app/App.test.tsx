import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { renderWithProviders, stubFetch } from '../test/render'
import { App } from './App'

afterEach(() => vi.unstubAllGlobals())

describe('navegação principal', () => {
  it('usa alvos de toque e rótulos legíveis no celular', () => {
    stubFetch([])
    renderWithProviders(<App />)
    const links = within(screen.getByRole('navigation', { name: 'Principal' })).getAllByRole('link')
    expect(links).toHaveLength(6)
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
})
