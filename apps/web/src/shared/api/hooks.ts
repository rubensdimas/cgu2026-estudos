import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useGameToast } from '../ui/GameToast'
import { api } from './client'
import type {
  DayOff, DayView, ListResponse, Mission, Occurrence, Session, SessionInput, Subject, Summary, WithDelta,
} from './types'

export const useSummary = () => useQuery({ queryKey: ['summary'], queryFn: () => api<Summary>('/game/summary') })

export const useDay = (day: string | undefined) =>
  useQuery({ queryKey: ['day', day], queryFn: () => api<DayView>(`/days/${day}`), enabled: !!day })

export const useOccurrences = (from: string, to: string) =>
  useQuery({
    queryKey: ['occurrences', from, to],
    queryFn: () => api<ListResponse<Occurrence>>(`/occurrences?from=${from}&to=${to}`),
  })

export const useSubjects = () =>
  useQuery({ queryKey: ['subjects'], queryFn: () => api<ListResponse<Subject>>('/subjects'), staleTime: Infinity })

export const useSessions = (day: string) =>
  useQuery({
    queryKey: ['sessions', day],
    queryFn: () => api<ListResponse<Session>>(`/sessions?from=${day}&to=${day}`),
  })

export const useDayOffs = () => useQuery({ queryKey: ['day-offs'], queryFn: () => api<ListResponse<DayOff>>('/day-offs') })

/** Mutação que mostra o efeito no jogo e atualiza HUD, dia e ciclo. */
function useGameMutation<V, R extends Partial<WithDelta> | void>(fn: (v: V) => Promise<R>) {
  const qc = useQueryClient()
  const toast = useGameToast()
  return useMutation({
    mutationFn: fn,
    onSuccess: (result) => {
      if (result && result.game_delta) toast(result.game_delta)
      for (const key of ['summary', 'day', 'occurrences', 'day-offs', 'sessions']) qc.invalidateQueries({ queryKey: [key] })
    },
  })
}

export const useCreateSession = () =>
  useGameMutation((s: SessionInput) => api<WithDelta>('/sessions', 'POST', s))

export const useDeleteSession = () => useGameMutation((id: string) => api<void>(`/sessions/${id}`, 'DELETE'))

export const useOpenDay = () =>
  useGameMutation((v: { day: string; occurrence_ids?: string[] }) =>
    api<Mission & WithDelta>(`/days/${v.day}/mission`, 'POST', { occurrence_ids: v.occurrence_ids ?? [] }))

export const useGenerateWeek = () =>
  useGameMutation((week_start: string) => api<WithDelta>('/plans/current/weeks', 'POST', { week_start }))

export const usePatchOccurrence = () =>
  useGameMutation((v: { id: string; body: Record<string, unknown> }) =>
    api<Occurrence & WithDelta>(`/occurrences/${v.id}`, 'PATCH', v.body))

export const useSetItemNa = () =>
  useGameMutation((v: { missionId: string; itemId: string; na_reason: string | null }) =>
    api<Mission & WithDelta>(`/missions/${v.missionId}/items/${v.itemId}`, 'PATCH', { na_reason: v.na_reason }))

export const useCheckout = () =>
  useGameMutation((v: { missionId: string; note: string }) =>
    api<Mission & WithDelta>(`/missions/${v.missionId}/checkout`, 'PUT', { note: v.note }))

export const usePutDayOff = () =>
  useGameMutation((v: DayOff) => api<WithDelta>(`/day-offs/${v.day}`, 'PUT', { reason: v.reason }))

export const useDeleteDayOff = () => useGameMutation((day: string) => api<void>(`/day-offs/${day}`, 'DELETE'))

export const usePutProgress = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (v: { topicId: string; status: string; version?: number }) =>
      api(`/topics/${v.topicId}/progress`, 'PUT', { status: v.status, version: v.version }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subjects'] }),
  })
}
