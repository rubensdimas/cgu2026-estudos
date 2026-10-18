import { usePatchOccurrence, usePlan } from '../../shared/api/hooks'
import type { Occurrence } from '../../shared/api/types'
import { addDays } from '../../shared/format'

/** Atalho: move o bloco para o dia seguinte, mesma janela. Some se amanhã passar do fim do plano. */
export function MoveTomorrowButton({ occ, today }: { occ: Occurrence; today: string }) {
  const plan = usePlan()
  const patch = usePatchOccurrence()
  const tomorrow = addDays(today, 1)
  if (!plan.data || tomorrow > plan.data.ends_on) return null
  return (
    <>
      <button onClick={() => patch.mutate({ id: occ.id, body: { version: occ.version, planned_on: tomorrow } })}
        disabled={patch.isPending} className="touch-target px-3 py-1 text-sm text-primary">
        Mover para amanhã
      </button>
      {patch.error && <p role="alert" className="w-full text-sm text-destructive">{patch.error.message}</p>}
    </>
  )
}
