import { PointsChart } from '@/components/ui/points-chart'
import { PointsLevelsTimeline } from '@/components/ui/points-levels-timeline'
import { StreakCalendar } from '@/components/ui/streak-calendar'
import { StreakCard } from '@/components/ui/streak-card'
import { useCalendar, useGameConfig, useSummary, useXpLedger } from '@/shared/api/hooks'
import type { Summary } from '@/shared/api/types'
import { mondayOf } from '@/shared/format'
import { QueryState } from '@/shared/ui/QueryState'
import { levelLines, toLevelsTimeline, toStreakPeriods, toXpSeries } from '@/shared/game/adapters'

const PLAN_START = '2026-10-09'

const FAILED = 'Não foi possível carregar o Progresso'

export function ProgressPage() {
  const summary = useSummary()
  if (!summary.data) return <QueryState title={FAILED} query={summary} />
  return <Dashboard s={summary.data} />
}

/** Só monta com o resumo carregado: as consultas dependentes usam a data de hoje do servidor. */
function Dashboard({ s }: { s: Summary }) {
  const today = s.today
  // O calendário mostra o mês e a semana inteiros: busca desde o que vier primeiro (dias fora do plano voltam neutros).
  const monthStart = `${today.slice(0, 7)}-01`
  const weekStart = mondayOf(today)
  const calendar = useCalendar(monthStart < weekStart ? monthStart : weekStart, today)
  // Busca até a prova: lançamentos datados no futuro (semana completa no domingo) entram no ponto de hoje.
  const ledger = useXpLedger(PLAN_START, s.exam_date)
  const config = useGameConfig()
  if (!calendar.data || !ledger.data || !config.data) {
    return <QueryState title={FAILED} query={[calendar, ledger, config].find((q) => !q.data)!} />
  }
  const periods = toStreakPeriods(calendar.data)
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Progresso</h1>
      <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
        XP mede constância, não preparo
      </p>
      <StreakCard streak={periods} neutralDates={calendar.data.neutral_days}
        currentStreak={s.streak.current} longestStreak={s.streak.best} total={s.streak.freezes_available}
        showHowItWorks />
      <section className="rounded-2xl border bg-card p-6">
        <StreakCalendar view="month" month={new Date(`${today}T12:00:00`)} startOfWeek={1}
          streak={periods} neutralDates={calendar.data.neutral_days} className="mx-auto" />
      </section>
      <PointsChart data={toXpSeries(ledger.data.items, PLAN_START, today)} levels={levelLines(s.level)}
        yAxisLabel="XP" title="XP acumulado" />
      <section className="rounded-2xl border bg-card p-6">
        <h2 className="mb-4 font-semibold">Níveis</h2>
        <PointsLevelsTimeline levels={toLevelsTimeline(config.data.levels)} currentPoints={s.xp_total}
          formatPoints={(v) => `${v.toLocaleString('pt-BR')}`} />
      </section>
    </div>
  )
}
