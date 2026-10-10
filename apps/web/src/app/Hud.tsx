import { useSummary } from '../shared/api/hooks'

export function Hud() {
  const { data } = useSummary()
  if (!data) return <div className="h-14 border-b border-border" aria-busy="true" />
  const pct = Math.min(100, Math.round((data.xp_into_level / data.xp_for_next) * 100))
  const s = data.streak
  return (
    <header className="sticky top-0 z-40 flex items-center gap-4 border-b border-border bg-background/95 px-4 py-2 backdrop-blur">
      <div className="min-w-0 flex-1">
        <p className="font-pixel text-sm font-semibold">
          Nv <span className="num">{data.level}</span> · {data.title}
        </p>
        <div className="mt-1 h-2 rounded-full bg-muted" role="progressbar" aria-label="XP do nível"
          aria-valuemin={0} aria-valuemax={data.xp_for_next} aria-valuenow={data.xp_into_level}>
          <div className="h-2 rounded-full bg-xp transition-all duration-300" style={{ width: `${pct}%` }} />
        </div>
      </div>
      <p className="num text-sm text-streak" title={`Recorde ${s.best}`}>
        🔥 {s.current}
        {s.freezes_available > 0 && <span className="ml-1 text-primary">❄{s.freezes_available}</span>}
        <span className="sr-only"> dias de sequência</span>
      </p>
      <p className="num font-pixel text-sm font-bold text-xp">D-{data.days_to_exam}</p>
    </header>
  )
}
