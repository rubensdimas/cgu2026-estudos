import { Link } from 'react-router-dom'

import { useReviews, useSummary } from '../../shared/api/hooks'
import type { Review } from '../../shared/api/types'
import { addDays, formatDay } from '../../shared/format'
import { CARD, CARD_BODY, CARD_TITLE } from '../../shared/ui/card'
import { QueryState } from '../../shared/ui/QueryState'
import { useTopicName } from './topics'

const UPCOMING_DAYS = 14

export function ReviewsPage() {
  const summary = useSummary()
  const today = summary.data?.today
  if (!today) return <QueryState title="Não foi possível carregar o dia" query={summary} />
  return <ReviewQueue today={today} />
}

function ReviewQueue({ today }: { today: string }) {
  const reviews = useReviews(today, addDays(today, UPCOMING_DAYS))
  const { data } = reviews
  const pending = data?.items.filter((r) => r.status === 'pending') ?? []
  const groups: [string, Review[], string][] = [
    ['Atrasadas', pending.filter((r) => r.late), 'Concluir uma revisão fecha as atrasadas do mesmo tópico.'],
    ['Hoje', pending.filter((r) => r.due_on === today), ''],
    ['Próximas', pending.filter((r) => r.due_on > today), `Até ${formatDay(addDays(today, UPCOMING_DAYS))}.`],
  ]
  return (
    <div className="space-y-4 md:space-y-6">
      <h1 className="text-xl font-bold">Revisões</h1>
      <p className="text-sm text-muted-foreground">
        Cada sessão de teoria agenda revisões do tópico para 1, 7 e 21 dias depois. Roteiro de 10 min: flashcards,
        5 questões CEBRASPE e análise de erros. Até 3 revisões por dia.
      </p>
      {!data && <QueryState title="Não foi possível carregar as revisões" query={reviews} />}
      {data && pending.length === 0 && (
        <p className="text-sm text-muted-foreground">Nenhuma revisão pendente. Elas aparecem depois de cada sessão de teoria.</p>
      )}
      {data && groups.filter(([, items]) => items.length > 0).map(([title, items, hint]) => (
        <section key={title} aria-label={title} className={CARD}>
          <h2 className={CARD_TITLE}>{title} <span className="num font-normal text-muted-foreground">{items.length}</span></h2>
          {hint && <p className="mt-1 text-sm text-muted-foreground">{hint}</p>}
          <ul className={`${CARD_BODY} divide-y divide-border`}>
            {items.map((r) => <ReviewRow key={r.id} review={r} />)}
          </ul>
        </section>
      ))}
    </div>
  )
}

export function ReviewRow({ review }: { review: Review }) {
  const topicName = useTopicName()
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2 text-sm">
      <span className={review.late ? 'text-streak' : 'text-muted-foreground'}>{formatDay(review.due_on)}</span>
      <span className="min-w-0 flex-1 basis-40 [overflow-wrap:anywhere]">{topicName(review.topic_id)}</span>
      <span className="text-muted-foreground">
        {review.cards_count === 0 ? 'Sem cartões' : `${review.cards_count} ${review.cards_count === 1 ? 'cartão' : 'cartões'}`}
      </span>
      <Link to={`/revisoes/${review.id}`} className="touch-target inline-flex items-center px-2 text-primary">Revisar</Link>
    </li>
  )
}
