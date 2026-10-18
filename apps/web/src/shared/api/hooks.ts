import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { CalendarDays, XpEntry } from '@/shared/game/adapters'

import { useGameToast } from '../ui/GameToast'
import { api, isConflict } from './client'
import type {
  DayOff, DayView, ExamVersion, GameConfig, Guidance, ListResponse, Mission, Occurrence, Plan, Session, SessionInput, Subject,
  Summary, TopicProgressOut, WithDelta,
} from './types'

export const useSummary = () => useQuery({ queryKey: ['summary'], queryFn: () => api<Summary>('/game/summary') })

export const useDay = (day: string | undefined) =>
  useQuery({ queryKey: ['day', day], queryFn: () => api<DayView>(`/days/${day}`), enabled: !!day })

export const useGuidance = (occurrenceId: string, enabled: boolean) =>
  useQuery({
    queryKey: ['guidance', occurrenceId],
    queryFn: () => api<Guidance>(`/occurrences/${occurrenceId}/guidance`),
    enabled,
  })

export const usePlan = () =>
  useQuery({ queryKey: ['plan'], queryFn: () => api<Plan>('/plans/current'), staleTime: Infinity })

export const useOccurrences = (from: string, to: string, enabled = true) =>
  useQuery({
    queryKey: ['occurrences', from, to],
    queryFn: () => api<ListResponse<Occurrence>>(`/occurrences?from=${from}&to=${to}`),
    enabled,
  })

export const useSubjects = () =>
  useQuery({ queryKey: ['subjects'], queryFn: () => api<ListResponse<Subject>>('/subjects'), staleTime: Infinity })

export const useCurrentExamVersion = () =>
  useQuery({ queryKey: ['exam-version'], queryFn: () => api<ExamVersion>('/exam-versions/current'), staleTime: Infinity })

export const useSessions = (day: string) =>
  useQuery({
    queryKey: ['sessions', day],
    queryFn: () => api<ListResponse<Session>>(`/sessions?from=${day}&to=${day}`),
  })

export const useCalendar = (from: string, to: string) =>
  useQuery({ queryKey: ['calendar', from, to], queryFn: () => api<CalendarDays>(`/game/calendar?from=${from}&to=${to}`) })

export const useXpLedger = (from: string, to: string) =>
  useQuery({ queryKey: ['xp', from, to], queryFn: () => api<ListResponse<XpEntry>>(`/game/xp?from=${from}&to=${to}`) })

export const useGameConfig = () =>
  useQuery({ queryKey: ['game-config'], queryFn: () => api<GameConfig>('/game/config'), staleTime: Infinity })

export const useDayOffs = () => useQuery({ queryKey: ['day-offs'], queryFn: () => api<ListResponse<DayOff>>('/day-offs') })

/** Mutação que mostra o efeito no jogo e atualiza HUD, dia e ciclo. */
function useGameMutation<V, R extends Partial<WithDelta> | void>(fn: (v: V) => Promise<R>) {
  const qc = useQueryClient()
  const toast = useGameToast()
  return useMutation({
    mutationFn: fn,
    onSuccess: (result) => {
      if (result && result.game_delta) toast(result.game_delta)
      for (const key of ['summary', 'day', 'occurrences', 'day-offs', 'sessions', 'calendar', 'xp', 'guidance']) qc.invalidateQueries({ queryKey: [key] })
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

/** Aplica o progresso confirmado ao catálogo em cache; em conflito, recarrega o catálogo. */
export const usePutProgress = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (v: { topicId: string; status: string; version?: number }) =>
      api<TopicProgressOut>(`/topics/${v.topicId}/progress`, 'PUT', { status: v.status, version: v.version }),
    onSuccess: ({ topic_id, ...progress }) =>
      qc.setQueryData<ListResponse<Subject>>(['subjects'], (old) => old && {
        ...old,
        items: old.items.map((s) => ({
          ...s, topics: s.topics.map((t) => (t.id === topic_id ? { ...t, progress } : t)),
        })),
      }),
    onError: (e) => { if (isConflict(e)) qc.invalidateQueries({ queryKey: ['subjects'] }) },
  })
}
