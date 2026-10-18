import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'

import { AchievementUnlocked } from '@/components/ui/achievement-unlocked'

import type { GameDelta } from '../api/types'
import { XP_SOURCE_LABEL } from '../format'

type Show = (delta: GameDelta) => void

const ToastContext = createContext<Show>(() => {})

export const useGameToast = () => useContext(ToastContext)

interface Toast { id: number; lines: string[] }

export function GameToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const [levelUp, setLevelUp] = useState<{ level: number; title: string } | null>(null)
  const show = useCallback<Show>((delta) => {
    const gains = delta.entries.filter((e) => e.xp > 0)
    if (delta.level_up) setLevelUp({ level: delta.level_up, title: delta.level_title ?? '' })
    if (gains.length === 0) return
    const id = Date.now() + Math.random()
    const lines = gains.map((e) => `+${e.xp} XP · ${XP_SOURCE_LABEL[e.source] ?? e.source}`)
    setToasts((t) => [...t, { id, lines }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000)
  }, [])
  return (
    <ToastContext.Provider value={show}>
      {children}
      <div aria-live="polite" className="fixed bottom-[calc(5rem+env(safe-area-inset-bottom))] right-4 z-50 flex flex-col gap-2 md:bottom-4">
        {toasts.map((t) => (
          <div key={t.id} className="rounded-lg border border-xp/40 bg-muted px-4 py-3 shadow-lg">
            {t.lines.map((line) => (
              <p key={line} className="num text-sm text-xp">{line}</p>
            ))}
          </div>
        ))}
      </div>
      {levelUp && (
        <AchievementUnlocked
          open
          onOpenChange={(open) => { if (!open) setLevelUp(null) }}
          achievement={{
            id: `nv-${levelUp.level}`,
            name: `Nível ${levelUp.level} · ${levelUp.title}`,
            description: 'XP mede constância, não preparo.',
            trigger: 'metric',
          }}
        />
      )}
    </ToastContext.Provider>
  )
}
