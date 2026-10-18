import { NetworkError } from '../api/client'

export type QueryLike = { isPending: boolean; isFetching: boolean; error: Error | null; refetch: () => unknown }

/** Carregamento ou falha de uma consulta sem dados; nada quando a consulta já tem dados. */
export function QueryState({ title, query }: { title: string; query: QueryLike }) {
  const { error, isFetching } = query
  if (error) {
    const detail = error instanceof NetworkError ? 'Salvar e consultar dependem do servidor (Mac ligado).' : error.message
    return (
      <div role="alert" className="rounded-lg border border-destructive/50 bg-card p-4">
        <p className="font-semibold">{title}</p>
        <p className="mt-1 text-sm text-muted-foreground">{detail}</p>
        <button type="button" onClick={() => query.refetch()} disabled={isFetching}
          className="touch-target mt-3 rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-60">
          {isFetching ? 'Tentando novamente…' : 'Tentar novamente'}
        </button>
      </div>
    )
  }
  if (query.isPending) return <p role="status" className="text-muted-foreground" aria-busy="true">Carregando…</p>
  return null
}
