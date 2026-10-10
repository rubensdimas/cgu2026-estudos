import { useState } from 'react'

import { useGenerateWeek, useOccurrences, usePatchOccurrence, useSummary } from '../../shared/api/hooks'
import type { Occurrence, Window } from '../../shared/api/types'
import { addDays, formatDay, mondayOf, PURPOSE_LABEL, WINDOW_LABEL } from '../../shared/format'

export function CyclePage() {
  const summary = useSummary()
  const [offset, setOffset] = useState(0)
  if (!summary.data) return <p className="text-muted" aria-busy="true">Carregando…</p>
  const weekStart = addDays(mondayOf(summary.data.today), offset * 7)
  return <Week weekStart={weekStart} onMove={(d) => setOffset((o) => o + d)} />
}

function Week({ weekStart, onMove }: { weekStart: string; onMove: (delta: number) => void }) {
  const weekEnd = addDays(weekStart, 6)
  const { data } = useOccurrences(weekStart, weekEnd)
  const generate = useGenerateWeek()
  const byDay = new Map<string, Occurrence[]>()
  for (const o of data?.items ?? []) byDay.set(o.planned_on, [...(byDay.get(o.planned_on) ?? []), o])
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button onClick={() => onMove(-1)} className="px-3 py-2 text-primary" aria-label="Semana anterior">←</button>
        <h1 className="font-display text-lg font-bold">Semana de {formatDay(weekStart)}</h1>
        <button onClick={() => onMove(1)} className="px-3 py-2 text-primary" aria-label="Próxima semana">→</button>
      </div>
      {data && data.items.length === 0 && (
        <div className="rounded-lg border border-border bg-surface p-4">
          <p className="text-sm text-muted">Semana ainda não gerada.</p>
          <button onClick={() => generate.mutate(weekStart)} className="mt-2 rounded-md bg-primary px-4 py-2 text-white">
            Gerar semana
          </button>
          {generate.error && <p role="alert" className="mt-2 text-sm text-danger">{generate.error.message}</p>}
        </div>
      )}
      {[...byDay.entries()].map(([day, occs]) => (
        <section key={day}>
          <h2 className="mb-2 font-display text-sm font-semibold uppercase text-muted">{formatDay(day)}</h2>
          <ul className="space-y-2">{occs.map((o) => <OccurrenceRow key={o.id} occ={o} />)}</ul>
        </section>
      ))}
    </div>
  )
}

export function OccurrenceRow({ occ }: { occ: Occurrence }) {
  const patch = usePatchOccurrence()
  const [moving, setMoving] = useState(false)
  const [date, setDate] = useState(occ.planned_on)
  const [window, setWindow] = useState<Window>(occ.window)
  const send = (body: Record<string, unknown>) => patch.mutate({ id: occ.id, body: { version: occ.version, ...body } })
  return (
    <li className="rounded-md bg-surface p-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{WINDOW_LABEL[occ.window]} · {occ.slot.title}</p>
          <p className="text-xs text-muted">
            {PURPOSE_LABEL[occ.slot.purpose]} · <span className="num">{occ.actual_minutes}/{occ.slot.minutes}</span> min ·{' '}
            {occ.status === 'completed' ? '✓ concluído' : occ.status === 'skipped' ? `— dispensado${occ.skip_reason ? ` (${occ.skip_reason})` : ''}` : 'pendente'}
          </p>
        </div>
        {occ.status === 'pending' && (
          <>
            <button onClick={() => setMoving((m) => !m)} className="px-2 py-1 text-sm text-primary">Remanejar bloco</button>
            <button onClick={() => {
              const reason = prompt('Motivo (opcional)')
              if (reason !== null) send({ status: 'skipped', skip_reason: reason })
            }}
              className="px-2 py-1 text-sm text-muted">Dispensar</button>
            {occ.actual_minutes > 0 && (
              <button onClick={() => send({ status: 'completed' })} className="px-2 py-1 text-sm text-success">Concluir</button>
            )}
          </>
        )}
        {occ.status !== 'pending' && (
          <button onClick={() => confirm('Reabrir este bloco? As sessões continuam registradas.') && send({ status: 'pending' })}
            className="px-2 py-1 text-sm text-muted">Reabrir</button>
        )}
      </div>
      {moving && (
        <div className="mt-2 flex flex-wrap items-end gap-2">
          <label className="text-sm">Data
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
              className="ml-1 rounded-md border border-border bg-surface-2 px-2 py-1" />
          </label>
          <label className="text-sm">Janela
            <select value={window} onChange={(e) => setWindow(e.target.value as Window)}
              className="ml-1 rounded-md border border-border bg-surface-2 px-2 py-1">
              {Object.entries(WINDOW_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <button onClick={() => { send({ planned_on: date, window }); setMoving(false) }}
            className="rounded-md bg-primary px-3 py-1 text-sm text-white">Salvar</button>
        </div>
      )}
      {patch.error && <p role="alert" className="mt-1 text-sm text-danger">{patch.error.message}</p>}
    </li>
  )
}
