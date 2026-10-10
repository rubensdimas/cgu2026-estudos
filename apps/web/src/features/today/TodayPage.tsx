import { useState } from 'react'
import { Link } from 'react-router-dom'

import { useCheckout, useDay, useOpenDay, usePutDayOff, useSetItemNa, useSubjects, useSummary } from '../../shared/api/hooks'
import type { DayView, MissionItem, Occurrence } from '../../shared/api/types'
import { WINDOW_LABEL } from '../../shared/format'
import { MissionRing } from './MissionRing'
import { SessionForm } from './SessionForm'

const STATE_LABEL = { pending: 'Pendente', done: '✓ Feito', not_applicable: '— Não se aplica' } as const

export function TodayPage() {
  const summary = useSummary()
  const today = summary.data?.today
  const day = useDay(today)
  const subjects = useSubjects()
  const [form, setForm] = useState<{ occurrence: Occurrence | null } | null>(null)

  if (!today || !day.data) return <p className="text-muted" aria-busy="true">Carregando…</p>
  const view = day.data

  return (
    <div className="space-y-4">
      <HolidayBanner />
      <StreakHint />
      {form ? (
        <SessionForm occurrence={form.occurrence} today={today} subjects={subjects.data?.items ?? []}
          onSaved={() => setForm(null)} onCancel={() => setForm(null)} />
      ) : (
        <>
          {view.mission ? (
            <MissionCard view={view} onRegister={(o) => setForm({ occurrence: o })} />
          ) : (
            <OpenDayCard view={view} />
          )}
          <button onClick={() => setForm({ occurrence: null })}
            className="w-full rounded-md border border-border px-4 py-2 text-sm text-muted hover:text-text">
            + Sessão avulsa
          </button>
        </>
      )}
    </div>
  )
}

function OpenDayCard({ view }: { view: DayView }) {
  const open = useOpenDay()
  if (!view.in_plan) return <p className="text-muted">Fora do período do plano.</p>
  const free = view.kind === 'free'
  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      <h2 className="font-display text-xl font-bold">{free ? 'Fim de semana' : 'Missão de hoje'}</h2>
      <p className="mt-1 text-sm text-muted">
        {free
          ? 'Sem ciclo planejado. Abra uma missão livre se quiser estudar; nada é cobrado.'
          : view.week_generated
            ? `${view.occurrences.length} blocos planejados para hoje.`
            : 'A semana ainda não foi gerada; abrir o dia também gera a semana.'}
      </p>
      <button onClick={() => open.mutate({ day: view.date })} disabled={open.isPending}
        className="mt-3 rounded-md bg-primary px-4 py-2 font-display font-semibold text-white">
        {free ? 'Abrir missão livre' : 'Abrir o dia'}
      </button>
      {open.error && <p role="alert" className="mt-2 text-sm text-danger">{open.error.message}</p>}
    </section>
  )
}

function MissionCard({ view, onRegister }: { view: DayView; onRegister: (o: Occurrence) => void }) {
  const mission = view.mission!
  const required = mission.items.filter((i) => i.required)
  const done = required.filter((i) => i.state !== 'pending').length
  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-center gap-4">
        <MissionRing done={done} total={required.length} />
        <div>
          <h2 className="font-display text-xl font-bold">
            {mission.complete ? 'Missão cumprida' : mission.kind === 'free' ? 'Missão livre' : 'Missão de hoje'}
          </h2>
          <p className="num text-sm text-xp">+{view.xp_today} XP hoje</p>
        </div>
      </div>
      <ul className="mt-4 space-y-2">
        {mission.items.map((item) => (
          <MissionRow key={item.id} item={item} missionId={mission.id} view={view} onRegister={onRegister} />
        ))}
      </ul>
    </section>
  )
}

function MissionRow({ item, missionId, view, onRegister }: {
  item: MissionItem; missionId: string; view: DayView; onRegister: (o: Occurrence) => void
}) {
  const setNa = useSetItemNa()
  if (item.kind === 'checkout') return <CheckoutRow missionId={missionId} item={item} note={view.mission!.checkout_note} />
  const occ = view.occurrences.find((o) => o.id === item.ref_id)
  return (
    <li className="flex flex-wrap items-center gap-2 rounded-md bg-surface-2 p-3">
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{occ ? `${WINDOW_LABEL[occ.window]} · ${occ.slot.title}` : 'Bloco remanejado'}</p>
        <p className="text-xs text-muted">{STATE_LABEL[item.state]}{item.na_reason ? ` (${item.na_reason})` : ''}</p>
      </div>
      {item.state === 'pending' && occ && (
        <>
          <button onClick={() => onRegister(occ)} className="rounded-md bg-primary px-3 py-1 text-sm text-white">
            Registrar sessão
          </button>
          <button onClick={() => setNa.mutate({ missionId, itemId: item.id, na_reason: 'Não se aplica hoje' })}
            className="rounded-md px-3 py-1 text-sm text-muted">Não se aplica hoje</button>
          <Link to="/ciclo" className="px-3 py-1 text-sm text-primary">Remanejar</Link>
        </>
      )}
      {item.na_reason && item.na_reason !== 'rescheduled' && item.na_reason !== 'skipped' && (
        <button onClick={() => setNa.mutate({ missionId, itemId: item.id, na_reason: null })}
          className="px-3 py-1 text-sm text-muted">Desfazer</button>
      )}
    </li>
  )
}

function CheckoutRow({ missionId, item, note }: { missionId: string; item: MissionItem; note: string | null }) {
  const [text, setText] = useState(note ?? '')
  const save = useCheckout()
  return (
    <li className="rounded-md bg-surface-2 p-3">
      <label className="block text-sm font-semibold">Check-out: o que ficou difícil hoje? <span className="text-xp">(bônus)</span>
        <textarea className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 font-normal" rows={2}
          maxLength={500} value={text} onChange={(e) => setText(e.target.value)} />
      </label>
      <button onClick={() => save.mutate({ missionId, note: text })}
        className="mt-2 rounded-md bg-primary px-3 py-1 text-sm text-white">
        {item.state === 'done' ? 'Atualizar' : 'Salvar check-out'}
      </button>
    </li>
  )
}

function StreakHint() {
  const { data } = useSummary()
  if (!data?.streak.at_stake_today) return null
  const left = data.streak.min_minutes - data.streak.minutes_today
  return <p className="text-sm text-streak">Hoje ainda conta: faltam <span className="num">{left}</span> min para manter a sequência.</p>
}

function HolidayBanner() {
  const { data } = useSummary()
  const put = usePutDayOff()
  const h = data?.holiday_suggestion
  if (!h) return null
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-md border border-border bg-surface p-3 text-sm">
      <span className="flex-1">{h.date === data!.today ? 'Hoje' : 'Amanhã'} é feriado ({h.label}). Marcar como folga?</span>
      <button onClick={() => put.mutate({ day: h.date, reason: h.label })} className="rounded-md bg-surface-2 px-3 py-1">
        Marcar folga
      </button>
    </div>
  )
}
