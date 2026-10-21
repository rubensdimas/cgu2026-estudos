import { useState } from 'react'

import { CONFLICT_MESSAGE, isConflict } from '../../shared/api/client'
import {
  useApproveFlashcards, useDeleteFlashcard, useFlashcardStatus, useGenerateFlashcards, usePatchFlashcard, useSessionFlashcards,
} from '../../shared/api/hooks'
import type { Flashcard, FlashcardCategory, Session } from '../../shared/api/types'
import { QueryState } from '../../shared/ui/QueryState'

export const CATEGORY_LABEL: Record<FlashcardCategory, string> = {
  conceito: 'Conceito',
  distincao: 'Distinção',
  condicao: 'Condição ou exceção',
  causa_consequencia: 'Causa e consequência',
  aplicacao: 'Aplicação',
  erro_recorrente: 'Erro recorrente',
  fundamentacao: 'Fundamentação',
}

const FIELD = 'touch-target mt-1 w-full rounded-md border border-border bg-muted px-3 py-2 text-sm'
const PRIMARY = 'touch-target rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-60'
const QUIET = 'touch-target rounded-md px-3 py-2 text-sm text-muted-foreground hover:text-foreground disabled:opacity-60'

const errorText = (e: unknown) => (isConflict(e) ? CONFLICT_MESSAGE : e instanceof Error ? e.message : 'Erro inesperado.')

/** Gera flashcards de uma sessão de teoria e revisa os rascunhos antes de irem para o baralho (R13). */
export function FlashcardPanel({ session }: { session: Session }) {
  const [studied, setStudied] = useState(session.notes)
  const status = useFlashcardStatus()
  const current = useSessionFlashcards(session.id)
  const generate = useGenerateFlashcards()
  const approveAll = useApproveFlashcards()
  const enabled = status.data?.enabled ?? false
  const cards = current.data?.cards ?? []
  const drafts = cards.filter((c) => c.status === 'draft').length
  const batch = current.data?.batch

  const run = () => generate.mutate({ sessionId: session.id, studied })

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm">O que estudei / errei
          <textarea className={FIELD} rows={3} maxLength={4000} value={studied} aria-describedby={`${session.id}-hint`}
            onChange={(e) => setStudied(e.target.value)} />
        </label>
        <p id={`${session.id}-hint`} className="mt-1 text-xs text-muted-foreground">
          A IA usa este texto e os subitens do edital do tópico. Nada fora deles vira cartão.
        </p>
      </div>
      {status.data && !enabled && (
        <p className="text-sm text-muted-foreground">Configure OPENAI_API_KEY no .env para gerar flashcards.</p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={PRIMARY} disabled={!enabled || generate.isPending} onClick={run}>
          {generate.isPending ? 'Gerando…' : batch ? 'Gerar novamente' : 'Gerar flashcards'}
        </button>
        {drafts > 0 && (
          <button type="button" className={QUIET} disabled={approveAll.isPending} onClick={() => approveAll.mutate(session.id)}>
            Aprovar todos
          </button>
        )}
      </div>
      {generate.error && !generate.isPending && (
        <div role="alert" className="flex flex-wrap items-center gap-2 text-sm text-destructive">
          <p>{errorText(generate.error)}</p>
          <button type="button" className="touch-target underline underline-offset-2" onClick={run}>Tentar novamente</button>
        </div>
      )}
      {approveAll.error && <p role="alert" className="text-sm text-destructive">{errorText(approveAll.error)}</p>}
      {!current.data && <QueryState title="Não foi possível carregar os flashcards" query={current} />}
      {batch && (
        <p className="text-sm text-muted-foreground">
          Base: {batch.origin}. Foco: {batch.focus}
          {cards.length === 0 && ' Nenhum cartão fiel ao conteúdo; complete o texto acima e gere novamente.'}
        </p>
      )}
      {cards.length > 0 && (
        <ul className="space-y-3">
          {cards.map((c) => <FlashcardItem key={c.id} card={c} />)}
        </ul>
      )}
    </div>
  )
}

/** Ficha com frente e verso separados por uma dobra tracejada; rascunhos podem ser aprovados, editados ou descartados. */
export function FlashcardItem({ card, onDelete }: { card: Flashcard; onDelete?: () => void }) {
  const [editing, setEditing] = useState(false)
  const [front, setFront] = useState(card.front)
  const [back, setBack] = useState(card.back)
  const patch = usePatchFlashcard()
  const remove = useDeleteFlashcard()
  const draft = card.status === 'draft'

  function save() {
    patch.mutate({ id: card.id, version: card.version, front, back }, { onSuccess: () => setEditing(false) })
  }

  return (
    <li className={`rounded-md border bg-muted ${draft ? 'border-dashed border-input' : 'border-border'}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 px-3 pt-3 text-xs text-muted-foreground">
        <span>{CATEGORY_LABEL[card.category]}</span>
        <span className="num">Subitem {card.subitem}</span>
      </div>
      {editing ? (
        <div className="space-y-2 p-3">
          <label className="block text-sm">Frente
            <textarea className={FIELD} rows={2} maxLength={2000} value={front} onChange={(e) => setFront(e.target.value)} />
          </label>
          <label className="block text-sm">Verso
            <textarea className={FIELD} rows={3} maxLength={2000} value={back} onChange={(e) => setBack(e.target.value)} />
          </label>
          <div className="flex gap-2">
            <button type="button" className={PRIMARY} disabled={patch.isPending || !front.trim() || !back.trim()} onClick={save}>
              Salvar
            </button>
            <button type="button" className={QUIET} onClick={() => { setEditing(false); setFront(card.front); setBack(card.back) }}>
              Cancelar
            </button>
          </div>
        </div>
      ) : (
        <>
          <p className="px-3 pb-3 pt-1 font-semibold leading-snug [overflow-wrap:anywhere]">{card.front}</p>
          <p className="border-t border-dashed border-input px-3 py-3 text-sm leading-relaxed text-muted-foreground [overflow-wrap:anywhere]">
            {card.back}
          </p>
        </>
      )}
      {!editing && (
        <div className="flex flex-wrap items-center gap-1 border-t border-border px-1 py-1">
          {draft ? (
            <button type="button" className="touch-target rounded-md px-3 py-2 text-sm font-semibold text-primary"
              disabled={patch.isPending} onClick={() => patch.mutate({ id: card.id, version: card.version, status: 'approved' })}>
              Aprovar
            </button>
          ) : (
            <span className="px-3 py-2 text-sm text-success">Aprovado</span>
          )}
          <button type="button" className={QUIET} onClick={() => setEditing(true)}>Editar</button>
          <button type="button" className={`${QUIET} ml-auto hover:text-destructive`} disabled={remove.isPending}
            onClick={() => (draft || confirm('Excluir este cartão do baralho?')) && remove.mutate(card.id, { onSuccess: onDelete })}>
            {draft ? 'Descartar' : 'Excluir'}
          </button>
        </div>
      )}
      {(patch.error || remove.error) && (
        <p role="alert" className="px-3 pb-3 text-sm text-destructive">{errorText(patch.error ?? remove.error)}</p>
      )}
    </li>
  )
}
