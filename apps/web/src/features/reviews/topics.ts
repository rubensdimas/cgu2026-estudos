import { useSubjects } from '../../shared/api/hooks'

/** "C02.01 Acesso à informação", ou só o código enquanto o catálogo não carrega. */
export function useTopicName() {
  const { data } = useSubjects()
  const titles = new Map(data?.items.flatMap((s) => s.topics.map((t) => [t.id, t.title] as const)))
  return (id: string) => `${id} ${titles.get(id) ?? ''}`.trim()
}
