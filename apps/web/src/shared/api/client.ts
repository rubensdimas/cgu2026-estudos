export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: Record<string, string>

  constructor(status: number, code: string, message: string, fields: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.code = code
    this.fields = fields
  }
}

export class NetworkError extends Error {}

export const CONFLICT_MESSAGE = 'Alterado em outro lugar; dados recarregados — revise e confirme de novo.'

/** Registro alterado em outro lugar: a versão enviada não é mais a atual. */
export const isConflict = (e: unknown): e is ApiError => e instanceof ApiError && e.code === 'version_conflict'

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export async function api<T>(path: string, method: Method = 'GET', body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(`/api/v1${path}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new NetworkError('Sem conexão com o servidor. Os dados só serão salvos após confirmação do servidor.')
  }
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const e = data.error ?? {}
    throw new ApiError(res.status, e.code ?? 'unknown', e.message ?? 'Erro inesperado.', e.fields ?? {})
  }
  return data as T
}
