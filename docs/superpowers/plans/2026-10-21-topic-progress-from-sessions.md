# Promoção automática do progresso por tópico — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sessões de teoria passam a promover o estado declarado do tópico no `/edital` (`in_progress` ou `first_pass`), inclusive retroativamente para as sessões já registradas.

**Architecture:** Um módulo de domínio em `apps/api/app/catalog/progress.py` concentra a regra "só promove" e é chamado pelos serviços de sessão (`study/service.py`) e de bloco (`planning/service.py`) dentro da mesma transação. Uma migração Alembic de dados chama a função de histórico do mesmo módulo. No front, só a invalidação do cache `subjects` após mutações de jogo.

**Tech Stack:** FastAPI + SQLAlchemy 2 + Alembic + pytest (integração em `cgu_test`); React + TanStack Query + vitest.

**Spec:** entendimento compartilhado do grilling (Q1–Q12), resumido abaixo.

## Regras (spec)

- Só sessões **ativas** (`deleted_at is null`) com `activity == "theory"` promovem.
- Sessão avulsa (`occurrence_id is null`) ou com bloco `completed` → `first_pass`; sessão em bloco `pending` → `in_progress`.
- Só promove: ordem `not_started < in_progress < first_pass < reviewed`; tópico sem `TopicProgress` conta como `not_started`. Nunca rebaixa.
- `declared_on` = `studied_on` da sessão que promoveu; linha existente recebe `version += 1`.
- Gatilhos: criar sessão; editar `topic_ids` (só tópicos novos); bloco passar a `completed` (via `PATCH /occurrences/{id}` ou via sessão com `complete_occurrence`) → sessões de teoria ativas do bloco promovem seus tópicos a `first_pass`; migração de dados única sobre o histórico (mais antiga primeiro).
- Nada reverte: excluir sessão, remover tópico, reabrir bloco.
- Sem aviso novo na UI; o cache `subjects` é invalidado após mutações de jogo.

## Global Constraints

- Textos de interface e docs em pt-BR; commits em inglês, Conventional Commits, terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Preservar volume `cgu2026_pgdata`, bancos `cgu` e `cgu_test` e pasta `backups/`. Não subir container sem pedido.
- `apps/web/.vitest/json/output.json` fica fora dos commits.
- Restauração (Q11): hoje só existe `scripts/restore.sh` (pg_dump), que já reproduz `topic_progress` como exportado. A restauração JSON (F5) ainda não existe; quando existir, não deve chamar este módulo. Nada a implementar agora.
- O `PUT /topics/{id}/progress` manual não muda.

## Review Focus

1. Sessão de teoria com vários tópicos, um deles já `reviewed` → só os outros mudam; o `reviewed` fica intacto (teste em Task 1).
2. Reenvio idempotente do mesmo `POST /sessions` não pode incrementar `version` de novo (teste em Task 2).
3. Sessão de teoria em bloco pendente seguida de outra sessão que conclui o bloco → tópico da primeira vira `first_pass` (teste em Task 2).
4. Migração rodando duas vezes ou sobre tópico já `first_pass` não altera `version`/`declared_on` (teste em Task 3).
5. Sessão excluída antes da conclusão do bloco não promove ao concluir o bloco (teste em Task 2).

---

### Task 1: Módulo de promoção

**Files:**
- Create: `apps/api/app/catalog/progress.py`
- Test: `apps/api/tests/integration/test_topic_progress.py`

**Interfaces:**
- Produces:
  - `promote(db: Session, topic_ids: Iterable[str], status: Literal["in_progress", "first_pass"], on: date) -> None` — cria ou sobe `TopicProgress` só quando `status` tem rank maior que o atual; faz `db.flush()`.
  - `promote_for_session(db: Session, session: StudySession, topic_ids: Iterable[str] | None = None) -> None` — no-op se a sessão não é teoria ou está excluída; `topic_ids=None` usa `session.topic_ids`; alvo conforme o bloco (regra acima); `on=session.studied_on`.
  - `promote_for_occurrence(db: Session, occurrence: Occurrence) -> None` — se `occurrence.status == "completed"`, chama `promote_for_session` para cada sessão de teoria ativa ligada ao bloco.
  - `promote_from_history(db: Session) -> None` — percorre sessões ativas de teoria ordenadas por `(studied_on, created_at)` e chama `promote_for_session`.

- [ ] **Step 1: Escrever testes falhando** (usam o fixture `db` de `tests/integration/conftest.py`, criando `StudySession`/`SessionTopic`/`TopicProgress` direto no ORM)
  - `test_promote_creates_and_raises_but_never_lowers`: sem linha → `promote(["C02.01"], "in_progress", d1)` cria `in_progress`/`d1`/`version 1`; `promote(..., "first_pass", d2)` → `first_pass`/`d2`/`version 2`; `promote(..., "in_progress", d3)` não altera nada (`version 2`, `declared_on d2`).
  - `test_promote_keeps_reviewed_topic_in_multi_topic_call`: C04.01 `reviewed` v1; `promote(["C02.01","C04.01"], "first_pass", d)` → C02.01 `first_pass`, C04.01 continua `reviewed` v1.
  - `test_promote_for_session_ignores_non_theory_and_deleted`: sessão `questions` e sessão de teoria com `deleted_at` preenchido → nenhum `TopicProgress` criado.
  - `test_promote_from_history_uses_earliest_qualifying_session`: duas sessões avulsas de teoria em C02.01 (`2026-10-05` e `2026-10-08`) → `first_pass`, `declared_on 2026-10-05`, `version 1`; chamar de novo mantém `version 1`.

- [ ] **Step 2: Rodar e ver falhar**
  Run: `docker compose --profile test run --rm test pytest tests/integration/test_topic_progress.py -v` (ajuste ao comando do serviço `test` no `README.md`)
  Expected: FAIL com `ModuleNotFoundError: app.catalog.progress`.

- [ ] **Step 3: Implementar `app/catalog/progress.py`** com as quatro funções acima; rank via tupla `("not_started", "in_progress", "first_pass", "reviewed")`. Docstring de módulo em pt-BR citando R08.

- [ ] **Step 4: Rodar e ver passar** (mesmo comando) — Expected: PASS.

- [ ] **Step 5: Commit** — `feat(api): add topic progress promotion rules`

### Task 2: Gatilhos em sessão e bloco

**Files:**
- Modify: `apps/api/app/study/service.py` (`create_session`, `update_session`)
- Modify: `apps/api/app/planning/service.py` (`patch_occurrence`)
- Test: `apps/api/tests/integration/test_topic_progress.py` (testes via `client`, reaproveitando o padrão `friday_blocks`/`payload` de `test_sessions.py`)

**Interfaces:**
- Consumes: `promote_for_session`, `promote_for_occurrence` (Task 1).

- [ ] **Step 1: Escrever testes falhando** (status lido de `GET /api/v1/subjects`)
  - `test_loose_theory_session_marks_first_pass`: `POST /sessions` teoria avulsa C02.01 em `2026-10-09` → `first_pass`, `declared_on 2026-10-09`.
  - `test_questions_session_does_not_change_progress`: `activity="questions"` → `progress` continua `None`.
  - `test_theory_in_pending_block_marks_in_progress_then_completion_promotes`: sessão de teoria num bloco de teoria de sexta com `complete_occurrence=False` → `in_progress`; `PATCH /occurrences/{id}` `{"status":"completed","version":…}` → `first_pass`.
  - `test_second_session_completing_block_promotes_first_session_topics`: sessão 1 (C02.01, sem concluir) + sessão 2 (C03.01, `complete_occurrence=True`) no mesmo bloco → ambos `first_pass`.
  - `test_resend_same_session_does_not_bump_version`: reenviar o mesmo corpo → `version` igual.
  - `test_editing_topics_promotes_only_new_ones_and_never_reverts`: sessão avulsa C02.01; `PATCH /sessions/{id}` `topic_ids=["C03.01"]` → C03.01 `first_pass`, C02.01 continua `first_pass`; `DELETE /sessions/{id}` → ambos continuam `first_pass`.
  - `test_deleted_session_does_not_promote_on_block_completion`: sessão de teoria A (C02.01) e sessão B (C03.01) em bloco pendente, excluir A, concluir bloco → C03.01 `first_pass`, C02.01 continua `in_progress`.

- [ ] **Step 2: Rodar e ver falhar** — Expected: asserts de `progress` falham (`None`).

- [ ] **Step 3: Ligar os gatilhos**
  - `create_session`: depois do bloco que conclui a ocorrência, `promote_for_session(db, session)` e, se a ocorrência ficou `completed` nesta chamada, `promote_for_occurrence(db, occurrence)`. O retorno antecipado de reenvio não chama nada.
  - `update_session`: quando `patch.topic_ids` vem, calcular `new = set(patch.topic_ids) - set(old)` antes de substituir os links e chamar `promote_for_session(db, session, new)` depois do flush.
  - `patch_occurrence`: quando `status == "completed"`, `promote_for_occurrence(db, occ)` após atribuir o status. Usar import tardio se houver ciclo de import, como já é feito com `guidance`.

- [ ] **Step 4: Rodar a suíte inteira da API** — `docker compose --profile test run --rm test` — Expected: tudo PASS (inclusive `test_sessions.py` e `test_planning.py`).

- [ ] **Step 5: Commit** — `feat(api): promote topic progress from theory sessions`

### Task 3: Migração de dados do histórico

**Files:**
- Create: `apps/api/migrations/versions/20261021_<rev>_topic_progress_backfill.py` (`down_revision = "5c9e1f3a7b21"`)
- Test: `apps/api/tests/integration/test_topic_progress.py`

**Interfaces:**
- Consumes: `promote_from_history` (Task 1).

- [ ] **Step 1: Teste do caso de borda (Review Focus 4)**
  - `test_promote_from_history_keeps_existing_first_pass_untouched`: C04.01 já `first_pass` v1 com `declared_on 2026-10-01` + sessão de teoria avulsa em C04.01 → depois de `promote_from_history`, `version 1` e `declared_on 2026-10-01`. Rodar, deve passar (a regra é da Task 1); se falhar, corrigir `promote`.

- [ ] **Step 2: Escrever a migração**
  `upgrade()`: `with Session(bind=op.get_bind()) as db: promote_from_history(db); db.flush()` (sem `commit`: o Alembic controla a transação). `downgrade()`: `pass` com comentário de que o estado declarado não é revertido (Q4). Comentário avisando que importa o ORM atual de propósito: app de usuário único, a migração roda uma vez.

- [ ] **Step 3: Verificar a migração contra uma cópia**, nunca contra `cgu` direto: `createdb -T cgu cgu_migcheck` no container `db`, rodar `alembic upgrade head` com `DATABASE_URL` apontando para `cgu_migcheck`, conferir `select topic_id, status, declared_on from topic_progress order by 1`.
  Expected: B03.01, C02.01, C03.01, E02.01 e E03.01 em `first_pass`; C04.01 inalterado; E01.02 ausente. Depois `dropdb cgu_migcheck`.

- [ ] **Step 4: Commit** — `feat(api): backfill topic progress from session history`

### Task 4: Front e documentação

**Files:**
- Modify: `apps/web/src/shared/api/hooks.ts` (`GAME_KEYS`)
- Test: `apps/web/src/features/today/SessionForm.test.tsx` ou teste novo de hook, seguindo o padrão local de mock de `api`
- Modify: `docs/03-regras-de-negocio.md` (R08), `docs/05-arquitetura-e-contratos.md` (linha do `PUT /topics/{id}/progress` e `GET /subjects`)

- [ ] **Step 1: Teste falhando**: após `useCreateSession` resolver, `queryClient.invalidateQueries` é chamado com `{ queryKey: ['subjects'] }`.
- [ ] **Step 2: Rodar** `rtk proxy npx vitest run` em `apps/web` — Expected: FAIL.
- [ ] **Step 3: Acrescentar `'subjects'` a `GAME_KEYS`.**
- [ ] **Step 4: Verificar** `npx tsc --noEmit -p .` e `rtk proxy npx vitest run` — Expected: PASS.
- [ ] **Step 5: Docs.** R08: trocar "Resultado de questões não altera automaticamente esse estado" por um parágrafo com as regras desta spec (teoria promove; só sobe; nada reverte; questões não alteram). `docs/05`: anotar na linha do `PUT /topics/{id}/progress` que o estado também é promovido por sessões de teoria (R08).
- [ ] **Step 6: Screenshots** do `/edital` em 360px e 1280px (`npx vite` com o compose ativo; `npx playwright screenshot --viewport-size=360,1600 --full-page`) para confirmar que nada mudou no layout; ler com a ferramenta Read.
- [ ] **Step 7: Commit** — `feat(web): refresh catalog after study mutations` + `docs: describe automatic topic progress promotion` (sem `output.json`).
