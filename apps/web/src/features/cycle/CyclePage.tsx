import { useState } from 'react'

import { CONFLICT_MESSAGE, isConflict } from '../../shared/api/client'
import { useGenerateWeek, useOccurrences, usePatchOccurrence, useSummary } from '../../shared/api/hooks'
import { QueryState } from '../../shared/ui/QueryState'
import { GuidancePanel } from '../guidance/GuidancePanel'
import type { Occurrence, Window } from '../../shared/api/types'
import { addDays, formatDay, mondayOf, PURPOSE_LABEL, WINDOW_LABEL } from '../../shared/format'

export function CyclePage() {
  const summary = useSummary()
  const [offset, setOffset] = useState(0)
  if (!summary.data) return <QueryState title="Não foi possível carregar o Ciclo" query={summary} />
  const weekStart = addDays(mondayOf(summary.data.today), offset * 7)
  return <Week weekStart={weekStart} onMove={(d) => setOffset((o) => o + d)} />
}

function Week({ weekStart, onMove }: { weekStart: string; onMove: (delta: number) => void }) {
  const weekEnd = addDays(weekStart, 6)
  const week = useOccurrences(weekStart, weekEnd)
  const { data } = week
  const generate = useGenerateWeek()
  const byDay = new Map<string, Occurrence[]>()
  for (const o of data?.items ?? []) byDay.set(o.planned_on, [...(byDay.get(o.planned_on) ?? []), o])
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button onClick={() => onMove(-1)} className="touch-target px-3 py-2 text-primary" aria-label="Semana anterior">←</button>
        <h1 className="text-lg font-bold">Semana de {formatDay(weekStart)}</h1>
        <button onClick={() => onMove(1)} className="touch-target px-3 py-2 text-primary" aria-label="Próxima semana">→</button>
      </div>
      {!data && <QueryState title="Não foi possível carregar a semana" query={week} />}
      {data && data.items.length === 0 && (
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Semana ainda não gerada.</p>
          <button onClick={() => generate.mutate(weekStart)} className="touch-target mt-2 rounded-md bg-primary px-4 py-2 text-primary-foreground">
            Gerar semana
          </button>
          {generate.error && <p role="alert" className="mt-2 text-sm text-destructive">{generate.error.message}</p>}
        </div>
      )}
      {[...byDay.entries()].map(([day, occs]) => (
        <section key={day}>
          <h2 className="mb-2 text-sm font-semibold uppercase text-muted-foreground">{formatDay(day)}</h2>
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
  const move = usePatchOccurrence()
  const send = (body: Record<string, unknown>) => patch.mutate({ id: occ.id, body: { version: occ.version, ...body } })
  const unchanged = date === occ.planned_on && window === occ.window
  function cancelMove() {
    setMoving(false)
    setDate(occ.planned_on)
    setWindow(occ.window)
    move.reset()
  }
  async function confirmMove() {
    try {
      await move.mutateAsync({ id: occ.id, body: { version: occ.version, planned_on: date, window } })
      setMoving(false)
    } catch {
      // O erro aparece junto ao formulário, que continua aberto com o rascunho.
    }
  }
  return (
    <li className="rounded-md bg-card p-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{WINDOW_LABEL[occ.window]} · {occ.slot.title}</p>
          <p className="text-xs text-muted-foreground">
            {PURPOSE_LABEL[occ.slot.purpose]} · <span className="num">{occ.actual_minutes}/{occ.slot.minutes}</span> min ·{' '}
            {occ.status === 'completed' ? '✓ concluído' : occ.status === 'skipped' ? `— dispensado${occ.skip_reason ? ` (${occ.skip_reason})` : ''}` : 'pendente'}
          </p>
        </div>
        {occ.status === 'pending' && (
          <>
            <button onClick={() => (moving ? cancelMove() : setMoving(true))} aria-expanded={moving}
              className="touch-target px-2 py-1 text-sm text-primary">Remanejar bloco</button>
            <button onClick={() => {
              const reason = prompt('Motivo (opcional)')
              if (reason !== null) send({ status: 'skipped', skip_reason: reason })
            }}
              className="touch-target px-2 py-1 text-sm text-muted-foreground">Dispensar</button>
            {occ.actual_minutes > 0 && (
              <button onClick={() => send({ status: 'completed' })} className="touch-target px-2 py-1 text-sm text-success">Concluir</button>
            )}
          </>
        )}
        {occ.status !== 'pending' && (
          <button onClick={() => confirm('Reabrir este bloco? As sessões continuam registradas.') && send({ status: 'pending' })}
            className="touch-target px-2 py-1 text-sm text-muted-foreground">Reabrir</button>
        )}
      </div>
      <div className="mt-2"><GuidancePanel occ={occ} /></div>
      {moving && (
        <div className="mt-2 space-y-2 rounded-md border border-border p-3">
          <div className="flex flex-wrap items-end gap-2">
            <label className="flex min-w-0 max-w-full flex-col gap-1 text-sm">Data
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
                className="touch-target w-full rounded-md border border-border bg-muted px-2 py-1" />
            </label>
            <label className="flex min-w-0 max-w-full flex-col gap-1 text-sm">Janela
              <select value={window} onChange={(e) => setWindow(e.target.value as Window)}
                className="touch-target w-full rounded-md border border-border bg-muted px-2 py-1">
                {Object.entries(WINDOW_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
          </div>
          {date && !unchanged && (
            <p className="text-sm">
              Mover de {formatDay(occ.planned_on)}, {WINDOW_LABEL[occ.window]}, para {formatDay(date)}, {WINDOW_LABEL[window]}.
            </p>
          )}
          {move.error && (
            <p role="alert" className="text-sm text-destructive">
              {isConflict(move.error) ? CONFLICT_MESSAGE : move.error.message}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <button onClick={confirmMove} disabled={!date || unchanged || move.isPending}
              className="touch-target rounded-md bg-primary px-3 py-1 text-sm text-primary-foreground disabled:opacity-50">
              {move.isPending ? 'Remanejando…' : 'Confirmar remanejamento'}
            </button>
            <button onClick={cancelMove} disabled={move.isPending} className="touch-target px-3 py-1 text-sm text-muted-foreground">
              Cancelar
            </button>
          </div>
        </div>
      )}
      {patch.error && <p role="alert" className="mt-1 text-sm text-destructive">{patch.error.message}</p>}
    </li>
  )
}
