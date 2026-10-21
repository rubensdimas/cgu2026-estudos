import { useState } from 'react'

import { useDeck, useDeleteFlashcard, useFlashcardSessions, useSubjects, useSummary } from '../../shared/api/hooks'
import type { Flashcard, FlashcardSessionItem } from '../../shared/api/types'
import { addDays, formatDay } from '../../shared/format'
import { CARD, CARD_BODY, CARD_DESC, CARD_TITLE } from '../../shared/ui/card'
import { QueryState } from '../../shared/ui/QueryState'
import { CATEGORY_LABEL, FlashcardPanel } from './FlashcardPanel'

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`

function cardsState({ drafts, approved }: FlashcardSessionItem): string {
  const parts = [drafts && plural(drafts, 'rascunho', 'rascunhos'), approved && plural(approved, 'aprovado', 'aprovados')]
  return parts.filter(Boolean).join(', ') || 'Sem cartões'
}

export function FlashcardsPage() {
  const summary = useSummary()
  const subjects = useSubjects()
  const today = summary.data?.today
  const titles = new Map(subjects.data?.items.flatMap((s) => s.topics.map((t) => [t.id, t.title] as const)))
  const topicName = (id: string) => `${id} ${titles.get(id) ?? ''}`.trim()

  return (
    <div className="space-y-4 md:space-y-6">
      <h1 className="text-xl font-bold">Cartões</h1>
      {today ? <TheorySessions today={today} topicName={topicName} /> : <QueryState title="Não foi possível carregar o dia" query={summary} />}
      <Deck topicName={topicName} />
    </div>
  )
}

function TheorySessions({ today, topicName }: { today: string; topicName: (id: string) => string }) {
  const sessions = useFlashcardSessions(addDays(today, -30), today)
  const [open, setOpen] = useState<string | null>(null)
  const { data } = sessions
  return (
    <section className={CARD}>
      <h2 className={CARD_TITLE}>Sessões de teoria</h2>
      <p className={CARD_DESC}>Últimos 30 dias. Gere cartões de uma sessão e aprove os que quiser revisar.</p>
      {!data && <QueryState title="Não foi possível carregar as sessões" query={sessions} />}
      {data?.items.length === 0 && (
        <p className={`${CARD_BODY} text-sm text-muted-foreground`}>
          Nenhuma sessão de teoria nos últimos 30 dias. Registre uma em Hoje para gerar cartões.
        </p>
      )}
      {data && data.items.length > 0 && (
        <ul className={`${CARD_BODY} divide-y divide-border`}>
          {data.items.map((item) => (
            <li key={item.session.id} className="py-2 text-sm">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="text-muted-foreground">{formatDay(item.session.studied_on)}</span>
                <span className="min-w-0 flex-1 basis-40 [overflow-wrap:anywhere]">{topicName(item.session.topic_ids[0])}</span>
                <span className="text-muted-foreground">{cardsState(item)}</span>
                <button className="touch-target px-2 py-1 text-primary" aria-expanded={open === item.session.id}
                  onClick={() => setOpen(open === item.session.id ? null : item.session.id)}>
                  Flashcards
                </button>
              </div>
              {open === item.session.id && <div className="pb-2 pt-3"><FlashcardPanel session={item.session} /></div>}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function Deck({ topicName }: { topicName: (id: string) => string }) {
  const deck = useDeck()
  const { data } = deck
  const groups = new Map<string, Flashcard[]>()
  for (const c of data?.items ?? []) groups.set(c.topic_id, [...(groups.get(c.topic_id) ?? []), c])
  return (
    <section className={CARD}>
      <h2 className={CARD_TITLE}>Baralho</h2>
      <p className={CARD_DESC}>Cartões aprovados, por tópico do edital.</p>
      {!data && <QueryState title="Não foi possível carregar o baralho" query={deck} />}
      {data?.total === 0 && (
        <p className={`${CARD_BODY} text-sm text-muted-foreground`}>
          Nenhum cartão aprovado ainda. Gere e aprove cartões a partir de uma sessão de teoria.
        </p>
      )}
      <div className={`${CARD_BODY} space-y-3 empty:hidden`}>
        {[...groups].map(([topicId, cards]) => (
          <details key={topicId} className="rounded-md border border-border p-3">
            <summary className="cursor-pointer font-semibold">
              <span>{topicName(topicId)}</span>
              <span className="num ml-2 font-normal text-muted-foreground">{plural(cards.length, 'cartão', 'cartões')}</span>
            </summary>
            <ul className="mt-3 space-y-3">
              {cards.map((c) => <DeckCard key={c.id} card={c} />)}
            </ul>
          </details>
        ))}
      </div>
    </section>
  )
}

function DeckCard({ card }: { card: Flashcard }) {
  const [shown, setShown] = useState(false)
  const remove = useDeleteFlashcard()
  return (
    <li className="rounded-md border border-border bg-muted">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 px-3 pt-3 text-xs text-muted-foreground">
        <span>{CATEGORY_LABEL[card.category]}</span>
        <span className="num">Subitem {card.subitem}</span>
      </div>
      <p className="px-3 pb-3 pt-1 font-semibold leading-snug [overflow-wrap:anywhere]">{card.front}</p>
      {shown && (
        <p className="border-t border-dashed border-input px-3 py-3 text-sm leading-relaxed text-muted-foreground [overflow-wrap:anywhere]">
          {card.back}
        </p>
      )}
      <div className="flex items-center gap-1 border-t border-border px-1 py-1">
        <button type="button" className="touch-target rounded-md px-3 py-2 text-sm font-semibold text-primary"
          aria-expanded={shown} onClick={() => setShown(!shown)}>
          {shown ? 'Esconder verso' : 'Mostrar verso'}
        </button>
        <button type="button" className="touch-target ml-auto rounded-md px-3 py-2 text-sm text-muted-foreground hover:text-destructive"
          disabled={remove.isPending} onClick={() => confirm('Excluir este cartão do baralho?') && remove.mutate(card.id)}>
          Excluir
        </button>
      </div>
      {remove.error && <p role="alert" className="px-3 pb-3 text-sm text-destructive">{remove.error.message}</p>}
    </li>
  )
}
