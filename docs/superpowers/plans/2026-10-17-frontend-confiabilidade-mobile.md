# Confiabilidade e uso móvel do frontend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task, inline and in order (no parallel subagents: `TodayPage.tsx` and `CyclePage.tsx` are edited by several tasks). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar as telas existentes mais claras diante de falhas de rede, dar confirmação confiável às gravações e melhorar a usabilidade por toque sem ampliar o escopo funcional do produto.

**Architecture:** Criar um estado compartilhado de carregamento/erro com ação de nova tentativa (`QueryState`) e aplicá-lo às consultas que bloqueiam Hoje, Ciclo, Edital, Progresso e Configurações, com consultas dependentes desabilitadas até que sua origem carregue. Tratar conflito de versão (409) recarregando a origem sem sobrescrever. No Edital, mostrar a versão vigente e a referência, com estado de gravação por tópico; no Ciclo, mostrar o destino e exigir confirmação explícita do remanejamento. Exibir erro em toda gravação que hoje falha em silêncio. Centralizar o alvo de toque em uma utility Tailwind e respeitar a safe area na navegação inferior.

**Tech Stack:** React 19, TypeScript 6, TanStack Query 5, Tailwind CSS 4, Vitest, Testing Library e Vite já instalados em `apps/web`.

**Spec:** [PRD](../../01-PRD.md), [UX e fluxos](../../06-ux-e-fluxos.md) (seção “Estados obrigatórios”), [validação e riscos](../../08-validacao-e-riscos.md) e auditoria frontend registrada na conversa de 2026-10-17, revisada em sessão de crítica (decisões Q1–Q20 abaixo).

**Linha de base:** `npx vitest run` em `apps/web` — 36 testes, 0 falhas (2026-10-17).

## Global Constraints

- Interface em pt-BR, tema escuro e identidade visual atual preservados.
- Usabilidade em 360 px; texto principal com pelo menos 16 px e rótulos com pelo menos 14 px.
- Navegação por teclado, foco visível, rótulos acessíveis e estados que não dependem só de cor.
- `prefers-reduced-motion` continua respeitado.
- Não exibir zero, lista vazia ou sucesso fictício enquanto uma consulta ou gravação não tiver confirmação do servidor.
- Em falha de rede, manter o conteúdo digitado nos formulários (sessão, check-out, remanejamento) e o UUID de envio da sessão.
- Conflito 409 nunca sobrescreve: recarrega a origem, avisa e pede nova confirmação.
- Não adicionar dependências nem mudar contratos da API; hooks podem ganhar parâmetros opcionais. O endpoint de versão atual do edital já existe.
- Este plano cobre as telas atuais; não implementar as jornadas futuras F2–F5.

## Decisões da revisão

| # | Decisão |
|---|---|
| Q1 | `useCalendar`/`useXpLedger` ganham `enabled` e só buscam com `summary.data`; sem fallback `PLAN_START` como data de consulta. Avaliação em ordem fixa (summary primeiro). `QueryState` usa `isPending` (inclui consultas desabilitadas), não `isLoading`. |
| Q2 | `QueryState` recebe `isFetching`; durante a nova tentativa o botão fica desabilitado e mostra “Tentando novamente…”. |
| Q3 | Título fixo por tela (“Não foi possível carregar …”) + `error.message` como detalhe; para `NetworkError`, texto “Salvar e consultar dependem do servidor (Mac ligado).” `client.ts` mantém suas mensagens. |
| Q4 | Hoje inclui erro de `subjects` dentro do `SessionForm` (rascunho e UUID preservados) e do `FreeBlockPicker`. `LateBlocks`, `GuidancePanel` e HUD ficam fora (riscos aceitos). |
| Q5 | Em `ApiError.status === 409`: invalidar a consulta de origem, avisar “Alterado em outro lugar; dados recarregados — revise e confirme de novo”, manter rascunho; a nova confirmação usa a versão recarregada. |
| Q6 | Seletor do tópico guarda o valor pendente localmente, fica desabilitado com “Salvando…” em texto; sucesso aplica a resposta do PUT via `setQueryData` (sem refetch do catálogo) e mostra “Salvo”; erro volta ao valor confirmado e alerta junto ao tópico. |
| Q7 | Falha de `/exam-versions/current` não bloqueia o catálogo (erro próprio na seção). `source_ref` da disciplina uma vez no `summary`; no tópico só o sufixo curto, sem `<details>` aninhado. Link `source_url` com `rel="noopener noreferrer"`. |
| Q8 | Sem etapa separada de prévia: resumo “De … → …” sempre visível no formulário; botão “Confirmar remanejamento” (desabilitado se destino = origem ou enviando) e “Cancelar”. `MoveTomorrowButton` fica fora. |
| Q9 | Branch `feat/frontend-confiabilidade-mobile`; primeiro commit é este plano; depois um commit por tarefa. |
| Q10 | `impeccable` opcional; `graphify update .` obrigatório; checagem visual via Claude in Chrome sobre `npm run dev` + API do docker compose, ou registrada como não verificada. |
| Q11 | Nova tarefa para gravações silenciosas: Remover folga, “Não se aplica hoje”/“Desfazer”, “Salvar check-out” (mantém texto) e folga do `HolidayBanner`. |
| Q12 | Todos os controles interativos das 5 telas, da navegação e do `QueryState` recebem o alvo de toque; texto e cartões não. |
| Q13 | `@utility touch-target { min-height: 44px; min-width: 44px; }` (sem `display`); links inline recebem `inline-flex items-center` no uso. |
| Q14 | Navegação: `px-0.5 text-sm leading-tight`; se transbordar em 360 px, rótulo pode quebrar ou ícone vira `size-4`, sem abreviar “Progresso”. `viewport-fit=cover`, `pb-[env(safe-area-inset-bottom)]` na navegação e reserva do conteúdo `calc(5rem + env(safe-area-inset-bottom))`. |
| Q15 | Cenários: (a) viewport 360 px; (b) 360 px com `html { font-size: 200% }` aplicado só na verificação. Critério: sem rolagem horizontal, nenhuma ação coberta pela navegação; em (b) a navegação pode quebrar rótulo. |
| Q16 | Um único teste de classe em `App.test.tsx` (navegação). Verificação real por script no Chrome que lista controles visíveis com `getBoundingClientRect` < 44 px; esperado: vazio ou exceções justificadas. |
| Q17 | Sete tarefas sequenciais, na ordem abaixo, execução inline. |
| Q18 | Verificação no Chrome é somente leitura contra o banco real: navegar, abrir formulários e `<details>`, medir; nunca submeter. Estados de gravação são cobertos apenas por testes com `stubFetch`. |
| Q19 | PR único para `main`, um commit por tarefa; descrição com riscos aceitos e resultado da checagem visual; `/code-review` do diff completo antes de abrir. |
| Q20 | Este documento registra as decisões; a implementação começa só após ordem explícita do usuário. |

## Riscos aceitos / fora do escopo

- `LateBlocks` retorna `null` quando sua consulta falha (blocos atrasados somem sem aviso).
- `GuidancePanel` mantém o tratamento atual de carregamento/erro.
- HUD mostra esqueleto enquanto o summary não carrega ou falha (não exibe zeros, mas não oferece nova tentativa).
- `MoveTomorrowButton` segue com um toque, sem confirmação (rótulo já explícito).
- Mensagens do `client.ts` não são alteradas.

## Review Focus

- Consulta inicial falha ou conexão cai: a tela explica a falha e permite tentar de novo, com retorno visível durante a nova tentativa — tarefas 1 e 2.
- Summary falha no Progresso: consultas dependentes não buscam intervalo errado e a tela não fica em branco — tarefa 1.
- Lista de tópicos indisponível: `SessionForm` não apresenta lista vazia como confirmada e preserva rascunho/UUID — tarefa 2.
- Gravação do tópico retorna erro ou 409: manter o último valor confirmado, indicar o tópico e, no 409, recarregar a versão — tarefa 3.
- Remanejamento falha (incluindo 409): formulário continua aberto com data e janela editadas, sem sucesso; nova confirmação usa a versão recarregada — tarefa 4.
- Nenhuma gravação falha em silêncio — tarefa 5.
- 360 px e fonte-base a 200%: ações alcançáveis, alvos ≥ 44 px, sem sobreposição, sem rolagem horizontal, safe area respeitada — tarefa 6.

---

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `apps/web/src/shared/ui/QueryState.tsx` | Estado de consulta pendente/erro com nova tentativa. |
| `apps/web/src/shared/ui/QueryState.test.tsx` | Comportamento acessível do estado compartilhado. |
| `apps/web/src/shared/api/client.ts` | Helper `isConflict(error)`. |
| `apps/web/src/shared/api/hooks.ts` | `enabled` em `useCalendar`/`useXpLedger`; `useCurrentExamVersion()`; `usePutProgress` com `setQueryData`. |
| `apps/web/src/shared/api/types.ts` | Tipo `ExamVersion` e retorno do PUT de progresso. |
| `apps/web/src/features/progress/ProgressPage.tsx` (+ `.test.tsx` novo) | Estados das consultas obrigatórias, sem gráfico parcial. |
| `apps/web/src/features/settings/SettingsPage.tsx` (+ `.test.tsx` novo) | Erro recuperável de folgas; erro de Remover folga. |
| `apps/web/src/features/today/TodayPage.tsx` (+ teste) | Estados de summary/day/sessions; `FreeBlockPicker`; gravações silenciosas. |
| `apps/web/src/features/today/SessionForm.tsx` (+ teste) | Erro de tópicos sem perder rascunho/UUID. |
| `apps/web/src/features/cycle/CyclePage.tsx` (+ teste) | Estado da semana; confirmação do remanejamento e 409. |
| `apps/web/src/features/catalog/CatalogPage.tsx` (+ `.test.tsx` novo) | Versão/referência do edital e gravação por tópico. |
| `apps/web/src/index.css` | `@utility touch-target`. |
| `apps/web/index.html` | `viewport-fit=cover`. |
| `apps/web/src/app/App.tsx` (+ `App.test.tsx` novo) | Navegação móvel: texto, alvo e safe area. |

## Task 1: `QueryState`, conflito e consultas dependentes (Progresso e Configurações)

**Interfaces:**
- Produces: `QueryState({ title, query }: { title: string; query: { isPending: boolean; isFetching: boolean; error: Error | null; refetch: () => unknown } })`. Pendente → texto de status com `aria-busy`. Erro → `role="alert"` com `title`, detalhe (`NetworkError` → “Salvar e consultar dependem do servidor (Mac ligado).”; demais → `error.message`) e botão “Tentar novamente” (`touch-target`, foco visível), desabilitado com rótulo “Tentando novamente…” enquanto `isFetching`. Neutro → nada.
- Produces: `isConflict(e: unknown): e is ApiError` em `client.ts` (`status === 409`).
- `useCalendar(from, to, enabled = true)` e `useXpLedger(from, to, enabled = true)`.
- Consumers só renderizam `QueryState` quando o dado necessário está ausente; erro de atualização em segundo plano não esconde dados carregados.

- [ ] **Step 1: RED de `QueryState`:** `renders_pending_error_and_retrying_states_accessibly` — pendente mostra status; erro mostra alerta, título, detalhe e botão que chama `refetch`; com `isFetching` o botão fica desabilitado com “Tentando novamente…”; `NetworkError` mostra o texto do servidor; neutro não renderiza. Rodar `rtk npm test -- src/shared/ui/QueryState.test.tsx` → falha.
- [ ] **Step 2: Implementar `QueryState`, `isConflict` e `enabled` nos hooks.** GREEN no mesmo comando.
- [ ] **Step 3: Progresso:** remover `?? PLAN_START` como data de consulta; `calendar`/`ledger` com `enabled: !!summary.data`; escolher a primeira consulta sem dados na ordem `summary`, `calendar`, `ledger`, `config` e passá-la ao `QueryState` com título “Não foi possível carregar o Progresso”. Nada do painel renderiza até todas terem dados.
- [ ] **Step 4: Configurações:** página e formulário continuam visíveis; a lista de folgas mostra `QueryState` (“Não foi possível carregar as folgas”) dentro da seção.
- [ ] **Step 5: Regressões:** `progress_shows_retry_and_skips_dependents_when_summary_fails` (não há fetch de `/game/calendar` nem `/game/xp`), `progress_does_not_render_partial_charts_when_ledger_fails`, `settings_shows_retry_when_day_off_query_fails` (formulário segue utilizável). RED → implementar → GREEN com `rtk npm test -- src/features/progress src/features/settings`.
- [ ] **Step 6: Commit:** `rtk git commit -m "fix: show recoverable query errors in progress and settings"`.

## Task 2: Hoje e semana do Ciclo

- [ ] **Step 1: RED:** `today_shows_retry_when_summary_fails`, `today_shows_retry_when_day_fails`, `today_sessions_shows_retry_when_list_query_fails`, `session_form_keeps_draft_and_id_when_topics_fail` (erro de `/subjects` dentro do formulário; campos e UUID preservados após nova tentativa bem-sucedida), `free_block_picker_shows_retry_when_week_fails`, `cycle_shows_retry_when_week_query_fails` (sem “Semana ainda não gerada”). Rodar `rtk npm test -- src/features/today src/features/cycle` → falhas novas.
- [ ] **Step 2: Implementar:** Hoje usa `QueryState` para summary e depois day; `TodaySessions` mostra `QueryState` em erro (não `null`); `SessionForm` recebe a consulta de tópicos (não `?? []`) e mostra erro/nova tentativa no campo de tópico sem desmontar o formulário; `FreeBlockPicker` e `Week` usam `QueryState`. Ciclo mantém o carregamento do summary via `QueryState`.
- [ ] **Step 3: GREEN** no mesmo comando; suíte inteira continua passando.
- [ ] **Step 4: Commit:** `rtk git commit -m "fix: show recoverable query errors in today and cycle"`.

## Task 3: Edital — versão, referência e gravação por tópico

**Interfaces:**
- API existente: `GET /api/v1/exam-versions/current` → `id`, `title`, `publication_date`, `source_url`, `source_sha256`, `exam_date`, `scoring_rules` (404 se não carregada). `GET /api/v1/subjects` inclui `source_ref` em disciplina e tópico. `PUT /api/v1/topics/{id}/progress` → `{ topic_id, status, declared_on, version }`; 409 `version_conflict`.
- Produces: `ExamVersion`, `useCurrentExamVersion()`; `usePutProgress` aplica a resposta em `['subjects']` via `setQueryData` (sem invalidar) e, em 409, invalida `['subjects']`.

- [ ] **Step 1: RED** em `CatalogPage.test.tsx`: `shows_current_exam_version_and_source_references`, `catalog_stays_usable_when_exam_version_fails`, `shows_catalog_retry_when_subjects_fail`, `shows_saving_then_saved_for_the_updated_topic_only`, `keeps_confirmed_value_and_shows_error_when_progress_save_fails`, `reloads_version_and_warns_on_progress_conflict` (após 409 há novo GET `/subjects`; nova escolha envia a versão recarregada).
- [ ] **Step 2: Implementar:** seção compacta com `title`, `publication_date` formatada e link `source_url` (`rel="noopener noreferrer"`); falha dessa consulta mostra `QueryState` próprio na seção. `source_ref` da disciplina no `summary`; no tópico só o sufixo após a última ` / `, em texto pequeno. Componente local `TopicStatus` com sua própria mutação: valor pendente local, `<select>` desabilitado e “Salvando…” em texto; sucesso → “Salvo” breve; erro → volta ao confirmado com `role="alert"` junto ao tópico; 409 → mensagem de conflito. Catálogo usa `QueryState` para `subjects`.
- [ ] **Step 3: GREEN** com `rtk npm test -- src/features/catalog`.
- [ ] **Step 4: Commit:** `rtk git commit -m "feat: show catalog sources and per-topic save status"`.

## Task 4: Confirmação do remanejamento

**Interfaces:** consome `OccurrenceRow`, `usePatchOccurrence()` e PATCH `{ version, planned_on, window }`. Em 409, invalidar `occurrences` e `day`; o `occ.version` recarregado chega por props.

- [ ] **Step 1: RED:** `shows_destination_summary_and_patches_only_on_confirm` (alterar data/janela mostra “De <dia> · <janela> → <dia> · <janela>”; nenhum PATCH antes de “Confirmar remanejamento”; depois, método, URL e payload com `version: 3`), `disables_confirm_when_destination_equals_origin`, `cancel_discards_draft`, `keeps_move_draft_open_after_server_error` (500: alerta, formulário aberto, valores preservados, sem sucesso), `reloads_and_keeps_draft_on_move_conflict` (409: alerta de conflito, novo GET de ocorrências, rascunho preservado).
- [ ] **Step 2: Implementar:** botão “Confirmar remanejamento” substitui “Salvar”; `await patch.mutateAsync(...)`; desabilitado enquanto pendente; fecha só no sucesso; erro mantém formulário; “Cancelar” fecha e restaura data/janela da ocorrência.
- [ ] **Step 3: GREEN** com `rtk npm test -- src/features/cycle`.
- [ ] **Step 4: Commit:** `rtk git commit -m "feat: confirm cycle moves before saving"`.

## Task 5: Gravações que falham em silêncio

- [ ] **Step 1: RED:** `settings_shows_error_when_removing_day_off_fails`, `checkout_keeps_text_and_shows_error_when_save_fails`, `not_applicable_shows_error_when_save_fails`.
- [ ] **Step 2: Implementar:** `role="alert"` com a mensagem junto à ação e botão desabilitado durante o envio em Remover folga, “Não se aplica hoje”/“Desfazer”, “Salvar check-out” (texto preservado) e folga do `HolidayBanner`.
- [ ] **Step 3: GREEN** com `rtk npm test -- src/features/settings src/features/today`.
- [ ] **Step 4: Commit:** `rtk git commit -m "fix: surface errors for silent mutations"`.

## Task 6: Alvos de toque, navegação e safe area

- [ ] **Step 1: RED:** `App.test.tsx` — `mobile_nav_links_use_touch_target_and_readable_labels` (cada link da navegação tem `touch-target` e `text-sm`).
- [ ] **Step 2: Implementar:** `@utility touch-target { min-height: 44px; min-width: 44px; }` em `index.css`; navegação com `px-0.5 text-sm leading-tight touch-target` e `pb-[env(safe-area-inset-bottom)]`; reserva do conteúdo `pb-[calc(5rem+env(safe-area-inset-bottom))] md:pb-0`; `viewport-fit=cover` no `index.html`. Aplicar `touch-target` a todo botão, link de ação, `select` e `input` das 5 telas, `SessionForm`, `OtherBlocks`, `LateBlocks`, `MoveTomorrow`, `GuidancePanel` e `QueryState`; links inline com `inline-flex items-center`.
- [ ] **Step 3: GREEN:** `rtk npm test`.
- [ ] **Step 4: Commit:** `rtk git commit -m "fix: enlarge touch targets and respect mobile safe area"`.

## Task 7: Verificação final

- [ ] Em `apps/web`: `rtk npm test`, `rtk npm run build`, `rtk npm run lint` — todos sem falhas.
- [ ] `rtk git diff --check main...` — sem erros de whitespace.
- [ ] Checagem visual **somente leitura** (Q18) com Claude in Chrome sobre `npm run dev` + API do docker compose, nos cenários (a) 360 px e (b) 360 px com `html { font-size: 200% }`, nas rotas `/`, `/ciclo`, `/edital`, `/progresso`, `/config`: sem rolagem horizontal (`document.documentElement.scrollWidth <= innerWidth`), navegação não cobre ações, foco visível, e script de medição listando `button, a, select, input` visíveis com largura ou altura < 44 px (esperado: vazio ou exceções justificadas). Nunca clicar em ações que gravam. Se o backend não subir, registrar como não verificado.
- [ ] Opcional: `rtk npx impeccable detect --json apps/web/src`.
- [ ] `graphify update .` na raiz.
- [ ] Conferir o diff: sem mudança de API, dependências, tema ou escopo F2–F5.
- [ ] `/code-review` do diff completo; abrir PR único para `main` com riscos aceitos e resultado da checagem visual.

## Handoff

Plano revisado para aprovação. Após aprovação: criar `feat/frontend-confiabilidade-mobile`, commitar este plano (`docs: plan frontend reliability and mobile usability`) e só iniciar a tarefa 1 após ordem explícita do usuário.
