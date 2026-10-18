import { GuidancePanel } from '../guidance/GuidancePanel'
import type { DayView, Occurrence } from '../../shared/api/types'
import { WINDOW_LABEL } from '../../shared/format'
import { MoveTomorrowButton } from './MoveTomorrow'

/** Blocos do dia que ficaram fora da missão (entraram depois de o dia ser aberto). */
export function OtherBlocks({ view, onRegister }: { view: DayView; onRegister: (o: Occurrence) => void }) {
  if (!view.mission) return null
  const inMission = new Set(view.mission.items.map((i) => i.ref_id))
  const others = view.occurrences.filter((o) => !inMission.has(o.id) && o.status !== 'skipped')
  if (others.length === 0) return null
  return (
    <section aria-label="Outros blocos de hoje" className="rounded-lg border border-border bg-card p-4">
      <h2 className="font-semibold">Outros blocos de hoje</h2>
      <p className="text-xs text-muted-foreground">Fora da missão: dão XP e concluem o bloco, mas não contam para a missão.</p>
      <ul className="mt-2 space-y-2">
        {others.map((o) => (
          <li key={o.id} className="flex flex-wrap items-center gap-2 rounded-md bg-muted p-3">
            <div className="min-w-0 flex-1">
              <p className="font-semibold">{WINDOW_LABEL[o.window]} · {o.slot.title}</p>
              <p className="text-xs text-muted-foreground">{o.status === 'completed' ? '✓ Feito' : 'Pendente'}</p>
            </div>
            {o.status === 'pending' && (
              <>
                <button onClick={() => onRegister(o)} className="touch-target rounded-md bg-primary px-3 py-1 text-sm text-primary-foreground">
                  Registrar sessão
                </button>
                <MoveTomorrowButton occ={o} today={view.date} />
              </>
            )}
            <GuidancePanel occ={o} />
          </li>
        ))}
      </ul>
    </section>
  )
}
