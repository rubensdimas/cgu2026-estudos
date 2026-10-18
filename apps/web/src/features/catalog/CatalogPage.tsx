import { useEffect, useState } from 'react'

import { isConflict } from '../../shared/api/client'
import { useCurrentExamVersion, usePutProgress, useSubjects } from '../../shared/api/hooks'
import type { Topic } from '../../shared/api/types'
import { QueryState } from '../../shared/ui/QueryState'

const STATUS = [
  ['not_started', 'Não iniciado'],
  ['in_progress', 'Em andamento'],
  ['first_pass', 'Primeira passagem'],
  ['reviewed', 'Revisado'],
] as const

const PAPER_COLOR = { P1: 'text-p1', P2: 'text-p2', P3: 'text-p3' } as const

const formatDate = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString('pt-BR')

export function CatalogPage() {
  const subjects = useSubjects()
  const { data } = subjects
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Edital</h1>
      <ExamVersionNote />
      <p className="text-sm text-muted-foreground">Cobertura declarada não mede domínio do conteúdo.</p>
      {!data && <QueryState title="Não foi possível carregar o Edital" query={subjects} />}
      {data?.items.map((s) => (
        <details key={s.id} className="rounded-lg border border-border bg-card p-3">
          <summary className="cursor-pointer font-semibold">
            <span className={`num mr-2 ${PAPER_COLOR[s.paper]}`}>{s.paper} {s.id}</span>{s.title}
            <span className="mt-0.5 block text-sm font-normal text-muted-foreground">Item {s.source_ref}</span>
          </summary>
          <ul className="mt-2 space-y-1">
            {s.topics.map((t) => <TopicRow key={t.id} topic={t} subjectRef={s.source_ref} />)}
          </ul>
        </details>
      ))}
    </div>
  )
}

function ExamVersionNote() {
  const version = useCurrentExamVersion()
  const { data } = version
  if (!data) return <QueryState title="Não foi possível carregar a versão do edital" query={version} />
  return (
    <p className="text-sm text-muted-foreground">
      Edital vigente:{' '}
      <a href={data.source_url} target="_blank" rel="noopener noreferrer" className="text-primary underline underline-offset-2">
        {data.title}
      </a>, publicado em {formatDate(data.publication_date)}.
    </p>
  )
}

/** Trecho da referência que identifica o tópico dentro do item da disciplina. */
const topicRef = (ref: string, subjectRef: string) =>
  ref.startsWith(`${subjectRef} / `) ? ref.slice(subjectRef.length + 3) : ref === subjectRef ? '' : ref

function TopicRow({ topic, subjectRef }: { topic: Topic; subjectRef: string }) {
  const put = usePutProgress()
  const [pending, setPending] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const confirmed = topic.progress?.status ?? 'not_started'
  const ref = topicRef(topic.source_ref, subjectRef)

  useEffect(() => {
    if (!saved) return
    const t = setTimeout(() => setSaved(false), 2500)
    return () => clearTimeout(t)
  }, [saved])

  function change(status: string) {
    setPending(status)
    setSaved(false)
    put.mutate({ topicId: topic.id, status, version: topic.progress?.version }, {
      onSuccess: () => setSaved(true),
      onSettled: () => setPending(null),
    })
  }

  return (
    <li className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
      <span className="num text-muted-foreground">{topic.id}</span>
      <span className="min-w-0 flex-1">
        {topic.title}
        {ref && <span className="block text-muted-foreground">{ref}</span>}
      </span>
      <select aria-label={`Estado de ${topic.id}`} value={pending ?? confirmed} disabled={pending !== null}
        onChange={(e) => change(e.target.value)}
        className="rounded-md border border-border bg-muted px-2 py-1 disabled:opacity-60">
        {STATUS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
      <span aria-live="polite" className="w-full text-right text-muted-foreground empty:hidden">
        {pending !== null ? 'Salvando…' : saved ? 'Salvo' : ''}
      </span>
      {put.error && !pending && (
        <p role="alert" className="w-full text-destructive">
          {isConflict(put.error) ? 'Alterado em outro lugar; dados recarregados — revise e confirme de novo.' : put.error.message}
        </p>
      )}
    </li>
  )
}
