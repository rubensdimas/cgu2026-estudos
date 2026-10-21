import { Flame, Settings, Snowflake } from 'lucide-react'
import { Link } from 'react-router-dom'

import { PointsBadge } from '@/components/ui/points-badge'

import { useSummary } from '../shared/api/hooks'

export function Hud() {
  const { data } = useSummary()
  if (!data) return <div className="h-14 border-b border-border" aria-busy="true" />
  const pct = Math.min(100, Math.round((data.xp_into_level / data.xp_for_next) * 100))
  const s = data.streak
  return (
    <header className="sticky top-0 z-30 flex items-center gap-4 border-b border-border bg-background/95 px-4 py-2 backdrop-blur">
      <div className="min-w-0 flex-1">
        <p className="font-pixel text-sm">
          Nv {data.level} · {data.title}
        </p>
        <div className="mt-1 h-2 rounded-full bg-muted" role="progressbar" aria-label="XP do nível"
          aria-valuemin={0} aria-valuemax={data.xp_for_next} aria-valuenow={data.xp_into_level}>
          <div className="h-2 rounded-full bg-xp transition-all duration-300" style={{ width: `${pct}%` }} />
        </div>
      </div>
      <PointsBadge name="XP" total={data.xp_total} size="sm" className="hidden sm:inline-flex" />
      <p className="flex items-center gap-1 font-mono text-sm text-streak" title={`Recorde ${s.best}`}>
        <Flame className="size-4" aria-hidden="true" />
        {s.current}
        {s.freezes_available > 0 && (
          <span className="ml-1 flex items-center gap-0.5 text-info">
            <Snowflake className="size-4" aria-hidden="true" />
            {s.freezes_available}
          </span>
        )}
        <span className="sr-only"> dias úteis de sequência</span>
      </p>
      <p className="font-pixel text-sm text-xp">D-{data.days_to_exam}</p>
      <Link to="/config" aria-label="Configurações"
        className="touch-target -mr-2 flex items-center justify-center px-2 text-muted-foreground hover:text-foreground md:hidden">
        <Settings className="size-5" aria-hidden="true" />
      </Link>
    </header>
  )
}
