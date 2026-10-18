import { useState, type FormEvent } from 'react'

import { ApiError } from '../../shared/api/client'
import { useCreateSession } from '../../shared/api/hooks'
import type { Activity, EssayKind, ListResponse, Occurrence, Subject } from '../../shared/api/types'
import { QueryState, type QueryLike } from '../../shared/ui/QueryState'

export type SubjectsQuery = QueryLike & { data?: ListResponse<Subject> }

interface Props {
  occurrence: Occurrence | null
  today: string
  subjects: SubjectsQuery
  onSaved: () => void
  onCancel: () => void
}

const ACTIVITY_LABEL: Record<Activity, string> = {
  theory: 'Teoria', questions: 'Questões', review: 'Revisão', essay: 'Discursiva',
}

function defaultEssayKind(o: Occurrence | null): EssayKind {
  return o?.slot.selection_mode === 'technical_case' ? 'technical_case' : 'complementary'
}

export function SessionForm({ occurrence, today, subjects, onSaved, onCancel }: Props) {
  const [id] = useState(() => crypto.randomUUID())
  const [activity, setActivity] = useState<Activity>(occurrence?.slot.activity ?? 'theory')
  const [topicId, setTopicId] = useState(occurrence?.suggested_topic_id ?? '')
  const [essayKind, setEssayKind] = useState<EssayKind>(defaultEssayKind(occurrence))
  const [minutes, setMinutes] = useState(String(occurrence?.slot.minutes ?? 60))
  const [studiedOn, setStudiedOn] = useState(today)
  const [notes, setNotes] = useState('')
  const [complete, setComplete] = useState(occurrence !== null)
  const [error, setError] = useState<{ message: string; fields: Record<string, string> } | null>(null)
  const create = useCreateSession()
  const isEssay = activity === 'essay'

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await create.mutateAsync({
        id,
        occurrence_id: occurrence?.id ?? null,
        studied_on: studiedOn,
        duration_minutes: Number(minutes),
        activity,
        essay_kind: isEssay ? essayKind : null,
        topic_ids: topicId ? [topicId] : [],
        notes,
        complete_occurrence: complete,
      })
      onSaved()
    } catch (err) {
      const fields = err instanceof ApiError ? err.fields : {}
      setError({ message: err instanceof Error ? err.message : 'Erro inesperado.', fields })
    }
  }

  const input = 'mt-1 w-full rounded-md border border-border bg-muted px-3 py-2'
  return (
    <form onSubmit={submit} className="space-y-3 rounded-lg border border-border bg-card p-4" aria-label="Registrar sessão">
      <h3 className="text-lg font-semibold">
        {occurrence ? `${occurrence.slot.code} · ${occurrence.slot.title}` : 'Sessão avulsa'}
      </h3>
      {!occurrence && (
        <label className="block text-sm">Atividade
          <select className={input} value={activity} onChange={(e) => setActivity(e.target.value as Activity)}>
            {Object.entries(ACTIVITY_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
      )}
      {isEssay && (
        <label className="block text-sm">Tipo de discursiva
          <select className={input} value={essayKind} onChange={(e) => setEssayKind(e.target.value as EssayKind)}>
            <option value="complementary">Complementar (até 30 linhas)</option>
            <option value="technical_case">Situação-problema de TI (até 60 linhas)</option>
          </select>
        </label>
      )}
      {subjects.data ? (
        <label className="block text-sm">Tópico {isEssay && '(opcional)'}
          <select className={input} value={topicId} onChange={(e) => setTopicId(e.target.value)} required={!isEssay}>
            <option value="">Selecione…</option>
            {subjects.data.items.map((s) => (
              <optgroup key={s.id} label={`${s.paper} · ${s.id} ${s.title}`}>
                {s.topics.map((t) => <option key={t.id} value={t.id}>{t.id} {t.title}</option>)}
              </optgroup>
            ))}
          </select>
        </label>
      ) : (
        <QueryState title="Não foi possível carregar os tópicos" query={subjects} />
      )}
      <div className="grid grid-cols-2 gap-3">
        <label className="block text-sm">Minutos
          <input className={`${input} num`} type="number" inputMode="numeric" min={1} max={720} required
            value={minutes} onChange={(e) => setMinutes(e.target.value)} />
        </label>
        <label className="block text-sm">Data
          <input className={input} type="date" max={today} required value={studiedOn}
            onChange={(e) => setStudiedOn(e.target.value)} />
        </label>
      </div>
      <label className="block text-sm">Observação
        <textarea className={input} rows={2} maxLength={2000} value={notes} onChange={(e) => setNotes(e.target.value)} />
      </label>
      {occurrence && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={complete} onChange={(e) => setComplete(e.target.checked)} />
          Concluir o bloco
        </label>
      )}
      {error && (
        <div role="alert" className="rounded-md border border-destructive/50 p-3 text-sm text-destructive">
          <p>{error.message}</p>
          {Object.entries(error.fields).map(([f, m]) => <p key={f}>{f}: {m}</p>)}
        </div>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={create.isPending}
          className="rounded-md bg-primary px-4 py-2 font-semibold text-primary-foreground disabled:opacity-60">
          {create.isPending ? 'Salvando…' : 'Registrar sessão'}
        </button>
        <button type="button" onClick={onCancel} className="rounded-md px-4 py-2 text-muted-foreground">Cancelar</button>
      </div>
    </form>
  )
}
