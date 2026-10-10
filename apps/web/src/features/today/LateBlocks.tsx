import { useState } from 'react'

import { useOccurrences, usePatchOccurrence, usePlan } from '../../shared/api/hooks'
import { addDays, formatDay } from '../../shared/format'

/** Aviso de blocos pendentes em dias passados; o usuário escolhe quais trazer para hoje. */
export function LateBlocks({ today }: { today: string }) {
  const plan = usePlan()
  const yesterday = addDays(today, -1)
  const startsOn = plan.data?.starts_on ?? today
  const enabled = !!plan.data && yesterday >= startsOn
  const { data } = useOccurrences(startsOn, yesterday, enabled)
  const patch = usePatchOccurrence()
  const [open, setOpen] = useState(false)
  const [chosen, setChosen] = useState<string[]>([])
  const late = (data?.items ?? []).filter((o) => o.status === 'pending')
  if (!enabled || late.length === 0) return null

  const toggle = (id: string) => setChosen((c) => (c.includes(id) ? c.filter((x) => x !== id) : [...c, id]))
  async function bring() {
    try {
      for (const o of late.filter((o) => chosen.includes(o.id))) {
        await patch.mutateAsync({ id: o.id, body: { version: o.version, planned_on: today } })
      }
      setChosen([])
      setOpen(false)
    } catch {
      // A mensagem aparece via patch.error.
    }
  }

  const n = late.length
  return (
    <section className="rounded-md border border-border bg-card p-3 text-sm">
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="font-semibold text-streak">
        {n} {n === 1 ? 'bloco atrasado' : 'blocos atrasados'} — escolher quais trazer para hoje
      </button>
      {open && (
        <fieldset className="mt-2 space-y-1">
          <legend className="sr-only">Blocos atrasados</legend>
          {late.map((o) => (
            <label key={o.id} className="flex items-center gap-2">
              <input type="checkbox" checked={chosen.includes(o.id)} onChange={() => toggle(o.id)} />
              {formatDay(o.planned_on)} · {o.slot.title}
            </label>
          ))}
          <button onClick={bring} disabled={chosen.length === 0 || patch.isPending}
            className="mt-2 rounded-md bg-primary px-3 py-1 text-primary-foreground disabled:opacity-50">
            Trazer para hoje
          </button>
        </fieldset>
      )}
      {patch.error && <p role="alert" className="mt-2 text-destructive">{patch.error.message}</p>}
    </section>
  )
}
