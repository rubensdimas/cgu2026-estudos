import { GuidancePanel } from '../guidance/GuidancePanel'
import type { DayView, Occurrence } from '../../shared/api/types'
import { WINDOW_LABEL } from '../../shared/format'
import { CARD, CARD_BODY, CARD_DESC, CARD_ROW, CARD_TITLE, ROW_PRIMARY_ACTION } from '../../shared/ui/card'
import { MoveTomorrowButton } from './MoveTomorrow'

/** Blocos do dia que ficaram fora da missão (entraram depois de o dia ser aberto). */
export function OtherBlocks({ view, onRegister }: { view: DayView; onRegister: (o: Occurrence) => void }) {
  if (!view.mission) return null
  const inMission = new Set(view.mission.items.map((i) => i.ref_id))
  const others = view.occurrences.filter((o) => !inMission.has(o.id) && o.status !== 'skipped')
  if (others.length === 0) return null
  return (
    <section aria-label="Outros blocos de hoje" className={CARD}>
      <h2 className={CARD_TITLE}>Outros blocos de hoje</h2>
      <p className={CARD_DESC}>Fora da missão: dão XP e concluem o bloco, mas não contam para a missão.</p>
      <ul className={`${CARD_BODY} space-y-3`}>
        {others.map((o) => (
          <li key={o.id} className={CARD_ROW}>
            <p className="font-semibold leading-snug [overflow-wrap:anywhere]">{WINDOW_LABEL[o.window]} · {o.slot.title}</p>
            <p className="mt-1 text-xs text-muted-foreground">{o.status === 'completed' ? '✓ Feito' : 'Pendente'}</p>
            {o.status === 'pending' && (
              <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                <button onClick={() => onRegister(o)} className={ROW_PRIMARY_ACTION}>
                  Registrar sessão
                </button>
                <div className="-mx-3 flex flex-wrap items-center sm:mx-0">
                  <MoveTomorrowButton occ={o} today={view.date} />
                </div>
              </div>
            )}
            <div className="mt-3 border-t border-border pt-1"><GuidancePanel occ={o} /></div>
          </li>
        ))}
      </ul>
    </section>
  )
}
