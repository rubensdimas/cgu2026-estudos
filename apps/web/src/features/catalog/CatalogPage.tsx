import { usePutProgress, useSubjects } from '../../shared/api/hooks'

const STATUS = [
  ['not_started', 'Não iniciado'],
  ['in_progress', 'Em andamento'],
  ['first_pass', 'Primeira passagem'],
  ['reviewed', 'Revisado'],
] as const

const PAPER_COLOR = { P1: 'text-p1', P2: 'text-p2', P3: 'text-p3' } as const

export function CatalogPage() {
  const { data } = useSubjects()
  const put = usePutProgress()
  if (!data) return <p className="text-muted" aria-busy="true">Carregando…</p>
  return (
    <div className="space-y-4">
      <h1 className="font-display text-xl font-bold">Edital</h1>
      <p className="text-sm text-muted">Cobertura declarada não mede domínio do conteúdo.</p>
      {data.items.map((s) => (
        <details key={s.id} className="rounded-lg border border-border bg-surface p-3">
          <summary className="cursor-pointer font-semibold">
            <span className={`num mr-2 ${PAPER_COLOR[s.paper]}`}>{s.paper} {s.id}</span>{s.title}
          </summary>
          <ul className="mt-2 space-y-1">
            {s.topics.map((t) => (
              <li key={t.id} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="num text-muted">{t.id}</span>
                <span className="min-w-0 flex-1">{t.title}</span>
                <select aria-label={`Estado de ${t.id}`} value={t.progress?.status ?? 'not_started'}
                  onChange={(e) => put.mutate({ topicId: t.id, status: e.target.value, version: t.progress?.version })}
                  className="rounded-md border border-border bg-surface-2 px-2 py-1">
                  {STATUS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </li>
            ))}
          </ul>
        </details>
      ))}
    </div>
  )
}
