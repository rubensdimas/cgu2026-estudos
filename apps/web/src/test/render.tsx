import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import { GameToastProvider } from '../shared/ui/GameToast'

export function renderWithProviders(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>
      <GameToastProvider>
        <MemoryRouter>{children}</MemoryRouter>
      </GameToastProvider>
    </QueryClientProvider>
  )
  return render(ui, { wrapper })
}

type Route = { method?: string; match: string; body: unknown; status?: number }

/** fetch falso que responde por método + trecho da URL e registra as chamadas. */
export function stubFetch(routes: Route[]) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    const route = routes.find((r) => (r.method ?? 'GET') === method && url.includes(r.match))
    if (!route) return new Response(JSON.stringify({}), { status: 404 })
    if (route.status === 204) return new Response(null, { status: 204 })
    return new Response(JSON.stringify(route.body), { status: route.status ?? 200 })
  })
  vi.stubGlobal('fetch', fn)
  return fn
}
