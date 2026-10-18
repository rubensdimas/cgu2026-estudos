import { useState, type FormEvent } from 'react'

import { useDayOffs, useDeleteDayOff, usePutDayOff } from '../../shared/api/hooks'
import { formatDay } from '../../shared/format'
import { QueryState } from '../../shared/ui/QueryState'

export function SettingsPage() {
  const dayOffs = useDayOffs()
  const put = usePutDayOff()
  const del = useDeleteDayOff()
  const [day, setDay] = useState('')
  const [reason, setReason] = useState('Feriado')

  function submit(e: FormEvent) {
    e.preventDefault()
    put.mutate({ day, reason })
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Configurações</h1>
      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="font-semibold">Folgas</h2>
        <p className="text-sm text-muted-foreground">Dia útil neutro para a sequência: não quebra nem conta.</p>
        <form onSubmit={submit} className="mt-3 flex flex-wrap items-end gap-2">
          <label className="text-sm">Data
            <input type="date" required value={day} onChange={(e) => setDay(e.target.value)}
              className="touch-target ml-1 rounded-md border border-border bg-muted px-2 py-1" />
          </label>
          <label className="text-sm">Motivo
            <input required maxLength={100} value={reason} onChange={(e) => setReason(e.target.value)}
              className="touch-target ml-1 rounded-md border border-border bg-muted px-2 py-1" />
          </label>
          <button disabled={put.isPending} className="touch-target rounded-md bg-primary px-3 py-1 text-sm text-primary-foreground disabled:opacity-60">
            Marcar folga
          </button>
        </form>
        {put.error && <p role="alert" className="mt-2 text-sm text-destructive">{put.error.message}</p>}
        {!dayOffs.data && <div className="mt-3"><QueryState title="Não foi possível carregar as folgas" query={dayOffs} /></div>}
        <ul className="mt-3 space-y-1">
          {dayOffs.data?.items.map((d) => (
            <li key={d.day} className="flex items-center gap-2 text-sm">
              <span className="flex-1">{formatDay(d.day)} · {d.reason}</span>
              <button onClick={() => del.mutate(d.day)} disabled={del.isPending} aria-label={`Remover folga de ${formatDay(d.day)}`}
                className="touch-target text-muted-foreground disabled:opacity-60">Remover</button>
            </li>
          ))}
        </ul>
        {del.error && <p role="alert" className="mt-2 text-sm text-destructive">{del.error.message}</p>}
      </section>
    </div>
  )
}
