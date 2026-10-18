import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ApiError, NetworkError } from '../api/client'
import { QueryState } from './QueryState'

const base = { isPending: false, isFetching: false, error: null, refetch: () => {} }

describe('QueryState', () => {
  it('mostra o carregamento enquanto a consulta não tem dados', () => {
    render(<QueryState title="Não foi possível carregar o Edital" query={{ ...base, isPending: true, isFetching: true }} />)
    expect(screen.getByRole('status')).toHaveTextContent('Carregando…')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('explica a falha e tenta de novo pelo botão', async () => {
    const refetch = vi.fn()
    render(<QueryState title="Não foi possível carregar o Edital"
      query={{ ...base, isPending: true, error: new ApiError(500, 'unknown', 'Erro inesperado.'), refetch }} />)
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Não foi possível carregar o Edital')
    expect(alert).toHaveTextContent('Erro inesperado.')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(refetch).toHaveBeenCalledOnce()
  })

  it('indica a nova tentativa em andamento e bloqueia toques repetidos', () => {
    render(<QueryState title="Falhou" query={{ ...base, isPending: true, isFetching: true, error: new Error('x') }} />)
    expect(screen.getByRole('button', { name: 'Tentando novamente…' })).toBeDisabled()
  })

  it('em falha de rede, explica que o servidor precisa estar ligado', () => {
    render(<QueryState title="Falhou" query={{ ...base, isPending: true, error: new NetworkError('Sem conexão.') }} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Salvar e consultar dependem do servidor (Mac ligado).')
  })

  it('não renderiza nada quando não há carregamento nem erro', () => {
    const { container } = render(<QueryState title="Falhou" query={base} />)
    expect(container).toBeEmptyDOMElement()
  })
})
