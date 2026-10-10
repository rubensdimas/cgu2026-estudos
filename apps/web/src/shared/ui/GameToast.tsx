import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'

import type { GameDelta } from '../api/types'
import { XP_SOURCE_LABEL } from '../format'

type Show = (delta: GameDelta) => void

const ToastContext = createContext<Show>(() => {})

export const useGameToast = () => useContext(ToastContext)

interface Toast { id: number; lines: string[]; levelUp: number | null }

export function GameToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const show = useCallback<Show>((delta) => {
    const gains = delta.entries.filter((e) => e.xp > 0)
    if (gains.length === 0 && !delta.level_up) return
    const id = Date.now() + Math.random()
    const lines = gains.map((e) => `+${e.xp} XP · ${XP_SOURCE_LABEL[e.source] ?? e.source}`)
    setToasts((t) => [...t, { id, lines, levelUp: delta.level_up }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000)
  }, [])
  return (
    <ToastContext.Provider value={show}>
      {children}
      <div aria-live="polite" className="fixed bottom-20 right-4 z-50 flex flex-col gap-2 md:bottom-4">
        {toasts.map((t) => (
          <div key={t.id} className="rounded-lg border border-xp/40 bg-muted px-4 py-3 shadow-lg">
            {t.levelUp && <p className="text-lg font-bold text-xp">Nível {t.levelUp}!</p>}
            {t.lines.map((line) => (
              <p key={line} className="num text-sm text-xp">{line}</p>
            ))}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
