export function MissionRing({ done, total }: { done: number; total: number }) {
  const r = 28
  const c = 2 * Math.PI * r
  const pct = total === 0 ? 0 : done / total
  return (
    <svg width="72" height="72" viewBox="0 0 72 72" role="img" aria-label={`Missão: ${done} de ${total} obrigatórios`}>
      <circle cx="36" cy="36" r={r} fill="none" stroke="var(--muted)" strokeWidth="8" />
      <circle cx="36" cy="36" r={r} fill="none" stroke="var(--xp)" strokeWidth="8" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - pct)} transform="rotate(-90 36 36)"
        className="transition-all duration-300" />
      <text x="36" y="41" textAnchor="middle" className="num" fill="var(--foreground)" fontSize="14">
        {done}/{total}
      </text>
    </svg>
  )
}
