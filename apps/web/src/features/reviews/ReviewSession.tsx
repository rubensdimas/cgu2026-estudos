import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import {
  useCompleteReview, useDismissReview, useRateFlashcard, useReview, useSubjects, useSummary,
} from '../../shared/api/hooks'
import type { Flashcard, Rating } from '../../shared/api/types'
import { formatDay } from '../../shared/format'
import { CARD, CARD_BODY, CARD_DESC, CARD_TITLE, CARD_TITLE_PRIMARY, ROW_PRIMARY_ACTION } from '../../shared/ui/card'
import { QueryState } from '../../shared/ui/QueryState'
import { CATEGORY_LABEL } from '../flashcards/FlashcardPanel'
import { SessionForm } from '../today/SessionForm'
import { useTopicName } from './topics'

/** Roteiro de referência da revisão (10 min; até 3 por dia); o tempo real fica com o usuário. */
const STEPS = [
  ['Flashcards', 3],
  ['5 questões CEBRASPE do tópico', 5],
  ['Análise de erros sem consulta', 2],
] as const

const RATING_BUTTONS: [Rating, string, string][] = [
  ['lembrei', 'Lembrei e justifiquei', 'text-success'],
  ['parcial', 'Lembrei parcialmente', 'text-foreground'],
  ['palpite', 'Acertei por palpite', 'text-streak'],
  ['nao_lembrei', 'Não lembrei', 'text-destructive'],
]

export function ReviewSessionRoute() {
  const { id = '' } = useParams()
  return <ReviewSession reviewId={id} />
}

export function ReviewSession({ reviewId }: { reviewId: string }) {
  const review = useReview(reviewId)
  const summary = useSummary()
  const subjects = useSubjects()
  const topicName = useTopicName()
  const complete = useCompleteReview()
  const dismiss = useDismissReview()
  const navigate = useNavigate()
  const [registering, setRegistering] = useState(false)
  const { data } = review
  if (!data) return <QueryState title="Não foi possível carregar a revisão" query={review} />
  const today = summary.data?.today
  const back = () => navigate('/revisoes')

  if (registering && today) {
    return (
      <SessionForm occurrence={null} today={today} subjects={subjects} onSaved={back} onCancel={back}
        preset={{ activity: 'review', topicId: data.topic_id, minutes: 10 }} />
    )
  }

  const pending = data.status === 'pending'
  return (
    <div className="space-y-4 md:space-y-6">
      <section className={CARD}>
        <h1 className={CARD_TITLE_PRIMARY}>Revisão</h1>
        <p className="mt-2 font-semibold [overflow-wrap:anywhere]">{topicName(data.topic_id)}</p>
        <p className={CARD_DESC}>
          {data.offset_days} {data.offset_days === 1 ? 'dia' : 'dias'} após o estudo · para {formatDay(data.due_on)}
          {data.late && <span className="text-streak"> · atrasada</span>}
          {data.status === 'completed' && data.completed_on && ` · concluída em ${formatDay(data.completed_on)}`}
          {data.status === 'dismissed' && ' · dispensada'}
        </p>
        <ol className={`${CARD_BODY} space-y-1 text-sm`}>
          {STEPS.map(([label, minutes], i) => (
            <li key={label} className="flex gap-3">
              <span className="num w-4 text-muted-foreground">{i + 1}</span>
              <span className="flex-1">{label}</span>
              <span className="num text-muted-foreground">{minutes} min</span>
            </li>
          ))}
        </ol>
        <p className="mt-2 text-xs text-muted-foreground">Questões e análise de erros você faz fora do app.</p>
      </section>

      <section className={CARD}>
        <h2 className={CARD_TITLE}>Flashcards</h2>
        {data.cards.length === 0 ? (
          <div className={`${CARD_BODY} text-sm`}>
            <p className="text-muted-foreground">Este tópico ainda não tem cartões aprovados.</p>
            <Link to="/cartoes" className="touch-target inline-flex items-center text-primary">Gerar cartões</Link>
          </div>
        ) : (
          <CardDeck cards={data.cards} />
        )}
      </section>

      {pending && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <button type="button" className={`${ROW_PRIMARY_ACTION} disabled:opacity-60`} disabled={complete.isPending}
            onClick={() => complete.mutate(data.id, { onSuccess: () => setRegistering(true) })}>
            Concluir revisão
          </button>
          <button type="button" className="touch-target rounded-md px-4 py-2 text-sm text-muted-foreground"
            disabled={dismiss.isPending}
            onClick={() => confirm('Dispensar esta revisão? Ela sai da fila sem XP.') && dismiss.mutate(data.id, { onSuccess: back })}>
            Dispensar
          </button>
        </div>
      )}
      {(complete.error || dismiss.error) && (
        <p role="alert" className="text-sm text-destructive">{(complete.error ?? dismiss.error)!.message}</p>
      )}
    </div>
  )
}

/** Um cartão por vez: frente, verso sob demanda e autoavaliação que avança. */
function CardDeck({ cards }: { cards: Flashcard[] }) {
  const [index, setIndex] = useState(0)
  const [shown, setShown] = useState(false)
  const rate = useRateFlashcard()
  if (index >= cards.length) {
    return (
      <div className={`${CARD_BODY} text-sm`}>
        <p>{cards.length} {cards.length === 1 ? 'cartão revisado' : 'cartões revisados'}. Siga para as questões.</p>
        <button type="button" className="touch-target -ml-3 px-3 text-primary" onClick={() => { setIndex(0); setShown(false) }}>
          Revisar de novo
        </button>
      </div>
    )
  }
  const card = cards[index]
  function answer(rating: Rating) {
    rate.mutate({ id: card.id, rating })
    setIndex(index + 1)
    setShown(false)
  }
  return (
    <div className={CARD_BODY}>
      <p className="num mb-2 text-xs text-muted-foreground">Cartão {index + 1} de {cards.length}</p>
      <article className="rounded-md border border-border bg-muted">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 px-3 pt-3 text-xs text-muted-foreground">
          <span>{CATEGORY_LABEL[card.category]}</span>
          <span className="num">Subitem {card.subitem}</span>
        </div>
        <p className="px-3 pb-4 pt-1 text-lg font-semibold leading-snug [overflow-wrap:anywhere]">{card.front}</p>
        {shown && (
          <p className="border-t border-dashed border-input px-3 py-4 leading-relaxed text-muted-foreground [overflow-wrap:anywhere]">
            {card.back}
          </p>
        )}
      </article>
      {shown ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {RATING_BUTTONS.map(([rating, label, tone]) => (
            <button key={rating} type="button" onClick={() => answer(rating)}
              className={`touch-target rounded-md border border-border bg-card px-2 py-2 text-sm font-medium ${tone}`}>
              {label}
            </button>
          ))}
        </div>
      ) : (
        <button type="button" className={`${ROW_PRIMARY_ACTION} mt-3`} onClick={() => setShown(true)}>Mostrar verso</button>
      )}
      {rate.error && <p role="alert" className="mt-2 text-sm text-destructive">Avaliação não salva: {rate.error.message}</p>}
    </div>
  )
}
