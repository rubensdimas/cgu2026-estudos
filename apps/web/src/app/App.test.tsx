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
    expect(links).toHaveLength(5)
    for (const link of links) {
      expect(link).toHaveClass('touch-target', 'text-sm')
      expect(link).not.toHaveClass('text-xs')
    }
  })
})
