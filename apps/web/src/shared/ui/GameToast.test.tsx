import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { GameDelta } from '../api/types'
import { GameToastProvider, useGameToast } from './GameToast'

function Trigger({ delta }: { delta: GameDelta }) {
  const show = useGameToast()
  return <button onClick={() => show(delta)}>disparar</button>
}

const levelUp: GameDelta = {
  xp_gained: 120, entries: [{ source: 'session_minutes', ref_id: 's', date: '2026-10-12', xp: 120 }],
  level_up: 2, level_title: 'Estagiário', mission_complete: [], streak: 2,
}

describe('diálogo de subida de nível', () => {
  it('abre com nível e título e fecha em Continuar', async () => {
    render(<GameToastProvider><Trigger delta={levelUp} /></GameToastProvider>)
    const user = userEvent.setup()
    await user.click(screen.getByText('disparar'))
    expect(screen.getByRole('dialog')).toHaveTextContent('Nível 2 · Estagiário')
    expect(screen.getByRole('dialog')).toHaveTextContent('XP mede constância, não preparo.')
    await user.click(screen.getByRole('button', { name: 'Continuar' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('fecha com Esc', async () => {
    render(<GameToastProvider><Trigger delta={levelUp} /></GameToastProvider>)
    const user = userEvent.setup()
    await user.click(screen.getByText('disparar'))
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('não abre sem subida de nível', async () => {
    render(<GameToastProvider><Trigger delta={{ ...levelUp, level_up: null, level_title: null }} /></GameToastProvider>)
    await userEvent.setup().click(screen.getByText('disparar'))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
