import { useState, type FormEvent } from 'react'

import { useDayOffs, useDeleteDayOff, usePutDayOff } from '../../shared/api/hooks'
import { formatDay } from '../../shared/format'

export function SettingsPage() {
  const { data } = useDayOffs()
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
      <h1 className="font-display text-xl font-bold">Configurações</h1>
      <section className="rounded-lg border border-border bg-surface p-4">
        <h2 className="font-display font-semibold">Folgas</h2>
        <p className="text-sm text-muted">Dia útil neutro para a sequência: não quebra nem conta.</p>
        <form onSubmit={submit} className="mt-3 flex flex-wrap items-end gap-2">
          <label className="text-sm">Data
            <input type="date" required value={day} onChange={(e) => setDay(e.target.value)}
              className="ml-1 rounded-md border border-border bg-surface-2 px-2 py-1" />
          </label>
          <label className="text-sm">Motivo
            <input required maxLength={100} value={reason} onChange={(e) => setReason(e.target.value)}
              className="ml-1 rounded-md border border-border bg-surface-2 px-2 py-1" />
          </label>
          <button className="rounded-md bg-primary px-3 py-1 text-sm text-white">Marcar folga</button>
        </form>
        {put.error && <p role="alert" className="mt-2 text-sm text-danger">{put.error.message}</p>}
        <ul className="mt-3 space-y-1">
          {data?.items.map((d) => (
            <li key={d.day} className="flex items-center gap-2 text-sm">
              <span className="flex-1">{formatDay(d.day)} · {d.reason}</span>
              <button onClick={() => del.mutate(d.day)} className="text-muted">Remover</button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
