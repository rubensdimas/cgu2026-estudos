import { useState } from 'react'
import { Link } from 'react-router-dom'

import {
  useCheckout, useDay, useDeleteSession, useOccurrences, useOpenDay, usePutDayOff, useSessions, useSetItemNa, useSubjects,
  useSummary,
} from '../../shared/api/hooks'
import type { DayView, MissionItem, Occurrence } from '../../shared/api/types'
import { addDays, formatDay, mondayOf, WINDOW_LABEL } from '../../shared/format'
import { CARD, CARD_BODY, CARD_DESC, CARD_ROW, CARD_TITLE, CARD_TITLE_PRIMARY, ROW_PRIMARY_ACTION } from '../../shared/ui/card'
import { QueryState } from '../../shared/ui/QueryState'
import { FlashcardPanel } from '../flashcards/FlashcardPanel'
import { GuidancePanel } from '../guidance/GuidancePanel'
import { LateBlocks } from './LateBlocks'
import { MissionRing } from './MissionRing'
import { MoveTomorrowButton } from './MoveTomorrow'
import { OtherBlocks } from './OtherBlocks'
import { SessionForm } from './SessionForm'

const DAY_FAILED = 'Não foi possível carregar o dia'

const STATE_LABEL = { pending: 'Pendente', done: '✓ Feito', not_applicable: '— Não se aplica' } as const

export function TodayPage() {
  const summary = useSummary()
  const today = summary.data?.today
  const day = useDay(today)
  const subjects = useSubjects()
  const [form, setForm] = useState<{ occurrence: Occurrence | null } | null>(null)

  if (!today) return <QueryState title={DAY_FAILED} query={summary} />
  if (!day.data) return <QueryState title={DAY_FAILED} query={day} />
  const view = day.data

  return (
    <div className="space-y-4 md:space-y-6">
      <HolidayBanner />
      <StreakHint />
      {view.in_plan && <LateBlocks today={today} />}
      {form ? (
        <SessionForm occurrence={form.occurrence} today={today} subjects={subjects}
          onSaved={() => setForm(null)} onCancel={() => setForm(null)} />
      ) : (
        <>
          {view.mission ? (
            <>
              <MissionCard view={view} onRegister={(o) => setForm({ occurrence: o })} />
              <OtherBlocks view={view} onRegister={(o) => setForm({ occurrence: o })} />
            </>
          ) : (
            <OpenDayCard view={view} />
          )}
          <button onClick={() => setForm({ occurrence: null })}
            className="touch-target w-full rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:text-foreground">
            + Sessão avulsa
          </button>
          <TodaySessions day={today} />
        </>
      )}
    </div>
  )
}

export function OpenDayCard({ view }: { view: DayView }) {
  const open = useOpenDay()
  const [chosen, setChosen] = useState<string[]>([])
  if (!view.in_plan) return <p className="text-muted-foreground">Fora do período do plano.</p>
  const free = view.kind === 'free'
  return (
    <section className={CARD}>
      <h2 className={CARD_TITLE_PRIMARY}>{free ? 'Fim de semana' : 'Missão de hoje'}</h2>
      <p className={CARD_DESC}>
        {free
          ? 'Sem ciclo planejado. Escolha até 2 blocos pendentes da semana para uma missão livre; nada é cobrado.'
          : view.week_generated
            ? `${view.occurrences.length} blocos planejados para hoje.`
            : 'A semana ainda não foi gerada; abrir o dia também gera a semana.'}
      </p>
      {free && <FreeBlockPicker day={view.date} chosen={chosen} onChange={setChosen} />}
      <button onClick={() => open.mutate({ day: view.date, occurrence_ids: chosen })}
        disabled={open.isPending || (free && chosen.length === 0)}
        className={`${ROW_PRIMARY_ACTION} ${CARD_BODY} disabled:opacity-50`}>
        {free ? 'Abrir missão livre' : 'Abrir o dia'}
      </button>
      {open.error && <p role="alert" className="mt-2 text-sm text-destructive">{open.error.message}</p>}
    </section>
  )
}

function FreeBlockPicker({ day, chosen, onChange }: {
  day: string; chosen: string[]; onChange: (ids: string[]) => void
}) {
  const monday = mondayOf(day)
  const week = useOccurrences(monday, addDays(monday, 6))
  const { data } = week
  if (!data) return <div className={CARD_BODY}><QueryState title="Não foi possível carregar os blocos da semana" query={week} /></div>
  const pending = data.items.filter((o) => o.status === 'pending')
  if (pending.length === 0) {
    return <p className={`${CARD_BODY} text-sm text-muted-foreground`}>Nenhum bloco pendente nesta semana. Use “Sessão avulsa”.</p>
  }
  const toggle = (id: string) =>
    onChange(chosen.includes(id) ? chosen.filter((c) => c !== id) : [...chosen, id])
  return (
    <fieldset className={`${CARD_BODY} space-y-1`}>
      <legend className="mb-1 text-sm font-semibold">Blocos pendentes (máx. 2)</legend>
      {pending.map((o) => (
        <label key={o.id} className="touch-target flex items-center gap-3 text-sm">
          <input type="checkbox" checked={chosen.includes(o.id)} onChange={() => toggle(o.id)}
            disabled={!chosen.includes(o.id) && chosen.length >= 2} />
          {formatDay(o.planned_on)} · {o.slot.title}
        </label>
      ))}
    </fieldset>
  )
}

export function TodaySessions({ day }: { day: string }) {
  const sessions = useSessions(day)
  const { data } = sessions
  const remove = useDeleteSession()
  const [open, setOpen] = useState<string | null>(null)
  if (!data) return <QueryState title="Não foi possível carregar as sessões de hoje" query={sessions} />
  if (data.items.length === 0) return null
  return (
    <section className={CARD}>
      <h2 className={CARD_TITLE}>Sessões de hoje</h2>
      <ul className={`${CARD_BODY} divide-y divide-border`}>
        {data.items.map((s) => (
          <li key={s.id} className="py-1 text-sm">
            <div className="flex items-center gap-3">
              <span className="num">{s.duration_minutes} min</span>
              <span className="min-w-0 flex-1 text-muted-foreground">{s.topic_ids.join(', ') || 'Discursiva'}</span>
              {s.activity === 'theory' && s.topic_ids.length > 0 && (
                <button className="touch-target px-2 py-1 text-primary" aria-expanded={open === s.id}
                  onClick={() => setOpen(open === s.id ? null : s.id)}>
                  Flashcards
                </button>
              )}
              <button aria-label={`Excluir sessão de ${s.duration_minutes} min`} className="touch-target -mr-2 px-2 py-1 text-destructive"
                onClick={() => confirm('Excluir esta sessão? Os minutos, o XP e a conclusão do bloco serão recalculados.')
                  && remove.mutate(s.id)}>
                Excluir
              </button>
            </div>
            {open === s.id && <div className="pb-3 pt-2"><FlashcardPanel session={s} /></div>}
          </li>
        ))}
      </ul>
      {remove.error && <p role="alert" className="mt-2 text-sm text-destructive">{remove.error.message}</p>}
    </section>
  )
}

function MissionCard({ view, onRegister }: { view: DayView; onRegister: (o: Occurrence) => void }) {
  const mission = view.mission!
  const required = mission.items.filter((i) => i.required)
  const done = required.filter((i) => i.state !== 'pending').length
  return (
    <section className={CARD}>
      <div className="flex items-center gap-4">
        <MissionRing done={done} total={required.length} />
        <div className="min-w-0">
          <h2 className={CARD_TITLE_PRIMARY}>
            {mission.complete ? 'Missão cumprida' : mission.kind === 'free' ? 'Missão livre' : 'Missão de hoje'}
          </h2>
          <p className="num mt-1 text-sm text-xp">+{view.xp_today} XP hoje</p>
        </div>
      </div>
      <ul className={`${CARD_BODY} space-y-3`}>
        {mission.items.map((item) => (
          <MissionRow key={item.id} item={item} missionId={mission.id} view={view} onRegister={onRegister} />
        ))}
      </ul>
    </section>
  )
}

export function MissionRow({ item, missionId, view, onRegister }: {
  item: MissionItem; missionId: string; view: DayView; onRegister: (o: Occurrence) => void
}) {
  const setNa = useSetItemNa()
  if (item.kind === 'checkout') return <CheckoutRow missionId={missionId} item={item} note={view.mission!.checkout_note} />
  const occ = view.occurrences.find((o) => o.id === item.ref_id)
  return (
    <li className={CARD_ROW}>
      <p className="font-semibold leading-snug [overflow-wrap:anywhere]">
        {occ ? `${WINDOW_LABEL[occ.window]} · ${occ.slot.title}` : 'Bloco remanejado'}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">{STATE_LABEL[item.state]}{item.na_reason ? ` (${item.na_reason})` : ''}</p>
      {item.state === 'pending' && occ && (
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
          <button onClick={() => onRegister(occ)} className={ROW_PRIMARY_ACTION}>
            Registrar sessão
          </button>
          <div className="-mx-3 flex flex-wrap items-center sm:mx-0">
            <button onClick={() => setNa.mutate({ missionId, itemId: item.id, na_reason: 'Não se aplica hoje' })}
              disabled={setNa.isPending} className="touch-target rounded-md px-3 py-1 text-sm text-muted-foreground">Não se aplica hoje</button>
            <MoveTomorrowButton occ={occ} today={view.date} />
            <Link to="/ciclo" className="touch-target inline-flex items-center px-3 py-1 text-sm text-primary">Remanejar</Link>
          </div>
        </div>
      )}
      {item.na_reason && item.na_reason !== 'rescheduled' && item.na_reason !== 'skipped' && (
        <button onClick={() => setNa.mutate({ missionId, itemId: item.id, na_reason: null })}
          disabled={setNa.isPending} className="touch-target -ml-3 mt-1 px-3 py-1 text-sm text-muted-foreground">Desfazer</button>
      )}
      {setNa.error && <p role="alert" className="mt-2 text-sm text-destructive">{setNa.error.message}</p>}
      {occ && <div className="mt-3 border-t border-border pt-1"><GuidancePanel occ={occ} /></div>}
    </li>
  )
}

export function CheckoutRow({ missionId, item, note }: { missionId: string; item: MissionItem; note: string | null }) {
  const [text, setText] = useState(note ?? '')
  const save = useCheckout()
  return (
    <li className={CARD_ROW}>
      <label className="block text-sm font-semibold leading-snug">Check-out: o que ficou difícil hoje? <span className="text-xp">(bônus)</span>
        <textarea className="touch-target mt-2 w-full rounded-md border border-border bg-card px-3 py-2 font-normal" rows={2}
          maxLength={500} value={text} onChange={(e) => setText(e.target.value)} />
      </label>
      <button onClick={() => save.mutate({ missionId, note: text })} disabled={save.isPending}
        className={`${ROW_PRIMARY_ACTION} mt-3 disabled:opacity-60`}>
        {item.state === 'done' ? 'Atualizar' : 'Salvar check-out'}
      </button>
      {save.error && <p role="alert" className="mt-2 text-sm text-destructive">{save.error.message}</p>}
    </li>
  )
}

function StreakHint() {
  const { data } = useSummary()
  if (!data?.streak.at_stake_today) return null
  const left = data.streak.min_minutes - data.streak.minutes_today
  return <p className="text-sm text-streak">Hoje ainda conta: faltam <span className="num">{left}</span> min para manter a sequência.</p>
}

export function HolidayBanner() {
  const { data } = useSummary()
  const put = usePutDayOff()
  const h = data?.holiday_suggestion
  if (!h) return null
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4 text-sm sm:flex-row sm:items-center">
      <span className="flex-1 leading-relaxed">{h.date === data!.today ? 'Hoje' : 'Amanhã'} é feriado ({h.label}). Marcar como folga?</span>
      <button onClick={() => put.mutate({ day: h.date, reason: h.label })} disabled={put.isPending}
        className="touch-target w-full rounded-md bg-muted px-4 py-2 disabled:opacity-60 sm:w-auto">
        Marcar folga
      </button>
      {put.error && <p role="alert" className="text-destructive sm:basis-full">{put.error.message}</p>}
    </div>
  )
}
