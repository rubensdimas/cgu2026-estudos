import { useState } from 'react'

import { useGuidance, usePatchOccurrence } from '../../shared/api/hooks'
import type { Guidance, Occurrence, Theme } from '../../shared/api/types'

const points = (v: number) => v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/** Painel recolhível com roteiro, tópico, materiais e, nas discursivas, tema e espelho. */
export function GuidancePanel({ occ }: { occ: Occurrence }) {
  const [open, setOpen] = useState(false)
  const { data, error } = useGuidance(occ.id, open)
  return (
    <div className="w-full">
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="text-sm text-primary">
        {open ? 'Ocultar orientações' : 'Como fazer este bloco'}
      </button>
      {open && !data && !error && <p aria-busy="true" className="text-sm text-muted-foreground">Carregando…</p>}
      {open && error && <p role="alert" className="text-sm text-destructive">{error.message}</p>}
      {open && data && <GuidanceBody occ={occ} g={data} />}
    </div>
  )
}

function GuidanceBody({ occ, g }: { occ: Occurrence; g: Guidance }) {
  return (
    <div className="mt-2 space-y-3 text-sm">
      <section>
        <h3 className="font-semibold">{g.roteiro.titulo}</h3>
        <ol className="mt-1 space-y-1">
          {g.roteiro.passos.map((p, i) => (
            <li key={i}><span className="num">{p.minutos} min</span> · {p.texto}</li>
          ))}
        </ol>
        {g.nota && <p className="mt-1 text-muted-foreground">{g.nota}</p>}
      </section>
      {g.topic && (
        <section>
          <h3 className="font-semibold"><span className="num">{g.topic.id}</span> · {g.topic.title}</h3>
          {g.topic.subitens.length > 0 && (
            <ul className="mt-1 list-disc pl-5 text-muted-foreground">
              {g.topic.subitens.map((s) => <li key={s}>{s}</li>)}
            </ul>
          )}
        </section>
      )}
      {g.materiais.length > 0 && (
        <section>
          <h3 className="font-semibold">Materiais</h3>
          <ul className="mt-1 space-y-1">
            {g.materiais.map((m) => (
              <li key={m.url}>
                <a href={m.url} target="_blank" rel="noreferrer" className="text-primary underline">{m.titulo}</a>
                {m.nota && <span className="text-muted-foreground"> — {m.nota}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}
      {g.tema && <ThemeView key={g.tema.id} occ={occ} tema={g.tema} nextId={g.next_theme_id} />}
      {g.lembretes.length > 0 && (
        <section>
          <h3 className="font-semibold">Regras do edital</h3>
          <ul className="mt-1 list-disc pl-5 text-muted-foreground">
            {g.lembretes.map((l) => <li key={l}>{l}</li>)}
          </ul>
        </section>
      )}
    </div>
  )
}

function ThemeView({ occ, tema, nextId }: { occ: Occurrence; tema: Theme; nextId: string | null }) {
  const [showKey, setShowKey] = useState(false)
  const patch = usePatchOccurrence()
  return (
    <section className="space-y-2 rounded-md border border-border p-3">
      <h3 className="font-semibold">{tema.titulo}</h3>
      <p className="text-xs text-muted-foreground">
        Até <span className="num">{tema.linhas}</span> linhas
        {tema.semelhante_a && (
          <> · semelhante a <a href={tema.semelhante_a.url} target="_blank" rel="noreferrer" className="underline">{tema.semelhante_a.prova}</a></>
        )}
      </p>
      <p className="whitespace-pre-line">{tema.texto_motivador}</p>
      <p className="font-semibold">{tema.comando}</p>
      <ol className="space-y-1">
        {tema.aspectos.map((a, i) => (
          <li key={i}><span className="num">{i + 1}</span> {a.texto} <span className="num text-muted-foreground">[valor: {points(a.valor)} pontos]</span></li>
        ))}
      </ol>
      <p className="text-xs text-muted-foreground">
        Fontes: {tema.fontes.map((f, i) => (
          <span key={f.url}>{i > 0 && '; '}<a href={f.url} target="_blank" rel="noreferrer" className="underline">{f.titulo}</a></span>
        ))}
      </p>
      <div className="flex flex-wrap gap-2">
        {!showKey && (
          <button onClick={() => setShowKey(true)} className="rounded-md bg-muted px-3 py-1">Ver pontos esperados</button>
        )}
        {nextId && (
          <button onClick={() => patch.mutate({ id: occ.id, body: { version: occ.version, theme_id: nextId } })}
            disabled={patch.isPending} className="px-3 py-1 text-primary">Trocar tema</button>
        )}
      </div>
      {patch.error && <p role="alert" className="text-destructive">{patch.error.message}</p>}
      {showKey && (
        <div aria-label="Pontos esperados" className="space-y-2 rounded-md bg-muted p-3">
          <p className="whitespace-pre-line">{tema.espelho.texto_padrao}</p>
          <ol className="space-y-1">
            {tema.espelho.quesitos.map((q) => (
              <li key={q.id}>
                <span className="num">{q.id}</span> {q.texto}
                <ul className="list-disc pl-5 text-muted-foreground">{q.conceitos.map((c) => <li key={c}>{c}</li>)}</ul>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  )
}
