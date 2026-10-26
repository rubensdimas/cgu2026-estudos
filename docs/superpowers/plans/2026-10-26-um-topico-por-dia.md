# 1 tópico por dia + revisões de 10 min — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar o ciclo de 3 blocos/dia por 1 bloco de 60 min por dia útil + até 30 min de revisões (3 × 10 min), e replanejar o histórico a partir de 26/10/2026.

**Architecture:** Template de ciclo novo (`effective_from` 26/10, 5 slots `T01`–`T05`) carregado pelo seed; funções puras novas em `app/domain` para sugestão de tópico, discursiva alternada e encaixe de revisões no limite diário; um comando idempotente `python -m app.replan` aplica a migração de dados uma única vez.

**Tech Stack:** FastAPI + SQLAlchemy + PostgreSQL (pytest via `docker compose --profile test run --rm test`), React/TS (vitest).

**Spec:** entendimento compartilhado da sessão de 26/10/2026 (grilling, Q1–Q16), resumido em "Decisões" abaixo.

## Decisões

- **D1** Dia útil = 1 bloco de 60 min (janela `before`). Seg: Específica, rodízio E01/E03; Ter: P2, rodízio C01→C05; Qua: Específica, rodízio E02/E04; Qui: P1, rodízio B01→B04; Sex: Discursiva alternada (semana par desde 26/10 = complementar, ímpar = situação-problema).
- **D2** Rodízio contado em semanas desde o `effective_from` do template (26/10 = semana 0 → E01, C01, E02, B01, complementar). Tópico sugerido = primeiro tópico da disciplina (por `position`) sem `first_pass`/`reviewed` declarado **antes** da data do bloco; disciplina esgotada → próxima da lista do slot.
- **D3** Revisões continuam em D+1/7/21. Roteiro de 10 min: Flashcards 3, 5 questões CEBRASPE 5, Análise de erros 2. Preset de sessão de revisão: 10 min.
- **D4** Limite de 3 revisões pendentes por dia. Ao criar uma revisão, se o dia estiver cheio, tenta os 2 dias seguintes; depois, o próximo sábado/domingo com vaga. Data ≥ prova → não cria.
- **D5** Missão de dia útil: até 3 revisões vencidas (mais antigas primeiro); a 1ª obrigatória, as demais opcionais (bônus). Fim de semana: inalterado (até 4 escolhidas).
- **D6** Meta semanal de minutos para "semana completa" vem do `weekly_minutes` do template vigente da semana (900 antes de 26/10, 300 depois); o histórico não muda.
- **D7** Settings: `weekly_goals` = `{"minutes": 300, "blocks": 5, "questions": {"P1": 15, "P2": 15, "P3": 30}, "essays": {"per_week": 1}, "missions": 5}`, `daily_question_goal` = 10.
- **D8** Etapas (`gamificacao.json`, só documentação/config — ainda não calculadas no código): ST2 = `topics_first_pass_in_stage` 16, `question_items` 200, `essays_total` 4; ST3 = `topics_first_pass_in_stage` 8, `overdue_reviews_at_end` 0, `timed_full_essays` 2. Chefões iguais, no fim de semana.
- **D9** Replanejamento único (`python -m app.replan`), idempotente:
  1. Blocos `pending` da semana 19/10 → `skipped`, `skip_reason` = `replanejamento: 1 tópico/dia`.
  2. Para cada tópico com sessão de teoria ativa, na ordem (`studied_on` da última sessão, `topic_id`): as revisões `pending` são reagendadas e as de offset faltante são criadas (na última sessão de teoria do tópico). Os 3 primeiros tópicos ficam com âncora no sábado 31/10, os 3 seguintes no domingo 01/11, e assim por diante em fins de semana. Datas: offset 1 → âncora, 7 → âncora + 7, 21 → âncora + 21. Offsets já `completed` não são tocados. Revisões pendentes que não são da última sessão do tópico → `dismissed`.
  3. Settings conforme D7.
  4. Gera a semana de 26/10 (`ensure_week`). Se a semana já existir com slots do template antigo, aborta sem gravar nada e explica.

## Global Constraints

- Textos de interface e docs em pt-BR; commits em inglês (Conventional Commits) com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Preservar volume `cgu2026_pgdata`, bancos `cgu`/`cgu_test` e `backups/`. Nada roda no banco `cgu` sem backup e sem confirmação do usuário (Task 8).
- `apps/web/.vitest/json/output.json` fica fora dos commits.
- UI dentro do sistema visual existente, validada em 360px.

## Review Focus

1. Tópico do bloco não pode "pular" depois que o próprio bloco é estudado (o estudo de hoje promove o tópico a `first_pass`); por isso D2 compara `declared_on < planned_on` → teste em Task 2.
2. Rodar `replan` duas vezes não pode criar revisões nem alterar datas de novo → teste em Task 5.
3. Sessão de teoria com 4+ tópicos no mesmo dia não pode pôr 4 revisões numa data → teste em Task 1.
4. Semanas antigas (900 min) não podem virar "completas" retroativamente com a meta nova → teste em Task 3.
5. Abrir o dia 26/10 antes do `replan` gera a semana com o template novo (seed já carregou) — não deve haver mistura; o `replan` detecta semana gerada pelo template antigo → teste em Task 5.

---

### Task 1: Limite diário de revisões

**Files:**
- Modify: `apps/api/app/domain/reviews.py`, `apps/api/app/reviews/service.py:17-33`
- Test: `apps/api/tests/unit/test_review_schedule.py`, `apps/api/tests/integration/test_reviews.py`
- Docs: `docs/03-regras-de-negocio.md` R07 (roteiro de 10 min, limite D4)

**Interfaces:**
- Produces: `DAILY_CAP = 3`; `place_due(due_on: date, load: Mapping[date, int], exam_on: date, cap: int = DAILY_CAP) -> date | None`

- [ ] **Step 1: Testes unitários**

```python
def test_place_due_keeps_free_day():
    assert place_due(date(2026, 10, 27), {}, EXAM) == date(2026, 10, 27)

def test_place_due_pushes_up_to_two_days():
    load = {date(2026, 10, 27): 3, date(2026, 10, 28): 3}
    assert place_due(date(2026, 10, 27), load, EXAM) == date(2026, 10, 29)

def test_place_due_falls_to_weekend():
    load = {date(2026, 10, 27): 3, date(2026, 10, 28): 3, date(2026, 10, 29): 3, date(2026, 10, 31): 3}
    assert place_due(date(2026, 10, 27), load, EXAM) == date(2026, 11, 1)

def test_place_due_never_reaches_exam():
    assert place_due(date(2026, 12, 12), {date(2026, 12, 12): 3}, EXAM) is None
```

- [ ] **Step 2:** `rtk proxy docker compose --profile test run --rm test pytest -q tests/unit/test_review_schedule.py` → FAIL (`place_due` não existe).
- [ ] **Step 3:** Implementar `place_due`: candidatos `due_on`, `+1`, `+2`; depois sábados/domingos seguintes; primeiro com `load.get(d, 0) < cap` e `d < exam_on`.
- [ ] **Step 4:** Teste de integração `test_session_with_four_topics_spreads_reviews`: sessão de teoria em 2026-10-09 com `C01.01, C02.01, C03.01, C04.01` → D+1 em 10/10 tem 3 revisões e a 4ª cai em 11/10.
- [ ] **Step 5:** Em `create_for_session`, carregar a contagem de pendentes por `due_on` uma vez e aplicar `place_due` depois de `is_duplicate`; `None` → não cria. Atualizar a contagem a cada revisão criada.
- [ ] **Step 6:** Rodar a suíte da API inteira; ajustar testes existentes que dependiam de >3 revisões no mesmo dia (só datas, não regras).
- [ ] **Step 7:** Atualizar R07 em `docs/03`. Commit `feat(api): cap pending reviews at three per day`.

### Task 2: Template de 1 bloco por dia e sugestão de tópico

**Files:**
- Create: `docs/data/ciclo-2026-10-26.json` (mesmo formato do bloco `template`/`weekly_minutes`/`slots` de `ciclo-inicial.json`; `origin` = `manual`, `weekly_minutes` = 300)
- Modify: `apps/api/app/seed.py` (carregar também os templates de `ciclo-*.json` além do inicial — extrair `ensure_template(db, plan, cycle_doc)`), `apps/api/app/domain/cycle.py`, `apps/api/app/planning/service.py:93-114`, `apps/api/app/guidance/service.py:13-62`
- Test: `apps/api/tests/unit/test_cycle.py`, `apps/api/tests/unit/test_guidance.py`, `apps/api/tests/integration/test_planning.py`, `apps/api/tests/integration/test_guidance.py`

**Slots do template novo** (todos `window` `before`, 60 min):

| code | weekday | purpose | activity | selection_mode | candidate_topic_ids (disciplinas) | title |
|---|---|---|---|---|---|---|
| T01 | 1 | specific | theory | `next_topic_rotation` | `["E01","E03"]` | Específica (E01/E03) |
| T02 | 2 | complementary | theory | `next_topic_rotation` | `["C01","C02","C03","C04","C05"]` | Conhecimentos complementares (P2) |
| T03 | 3 | specific | theory | `next_topic_rotation` | `["E02","E04"]` | Específica (E02/E04) |
| T04 | 4 | basic | theory | `next_topic_rotation` | `["B01","B02","B03","B04"]` | Conhecimentos básicos (P1) |
| T05 | 5 | essay | essay | `alternate_essay` | `[]` | Discursiva da semana |

**Interfaces:**
- Produces (em `app/domain/cycle.py`):
  - `weeks_since(week_start: date, effective_from: date) -> int`
  - `next_topic(subjects: list[str], weeks: int, topics_by_subject: Mapping[str, list[str]], done: set[str]) -> str | None` — começa em `subjects[weeks % len]` e avança circularmente até achar tópico fora de `done`.
  - `essay_kind_for(selection_mode: str, weeks: int) -> str | None` — `complementary`/`technical_case` passam direto; `alternate_essay` → par `complementary`, ímpar `technical_case`; outros → `None`.
- Produces (em `app/planning/service.py`): `suggested_topic(db: Session, occ: Occurrence) -> str | None` — usa `suggest_topic` para os modos antigos e `next_topic` para `next_topic_rotation`, com `done` = tópicos com `TopicProgress.status in (first_pass, reviewed)` e `declared_on < occ.planned_on`. `occurrence_out` e `guidance_out` passam a usá-la.

- [ ] **Step 1: Testes unitários** em `test_cycle.py`:

```python
def test_next_topic_rotation_starts_at_week_subject():
    topics = {"E01": ["E01.01", "E01.02"], "E03": ["E03.01", "E03.02"]}
    assert next_topic(["E01", "E03"], 0, topics, set()) == "E01.01"
    assert next_topic(["E01", "E03"], 1, topics, {"E03.01"}) == "E03.02"

def test_next_topic_skips_exhausted_subject():
    topics = {"E01": ["E01.01"], "E03": ["E03.01"]}
    assert next_topic(["E01", "E03"], 0, topics, {"E01.01"}) == "E03.01"
    assert next_topic(["E01", "E03"], 0, topics, {"E01.01", "E03.01"}) is None

def test_alternate_essay_by_week():
    assert essay_kind_for("alternate_essay", 0) == "complementary"
    assert essay_kind_for("alternate_essay", 1) == "technical_case"
    assert essay_kind_for("technical_case", 4) == "technical_case"
```

- [ ] **Step 2:** Rodar → FAIL. **Step 3:** Implementar as três funções.
- [ ] **Step 4: Testes de integração** (`test_planning.py`): com o seed, a semana de 2026-10-26 tem 5 ocorrências `T01`–`T05`, uma por dia; a de 2026-10-19 continua com 15. Com `TopicProgress` de `E02.01` em `first_pass` (declared 2026-10-20), a sugestão de 2026-10-28 é `E02.02`; com `E01.01` `first_pass` declarado em 2026-10-26, a sugestão do bloco de 2026-10-26 continua `E01.01` (Review Focus 1).
- [ ] **Step 5:** Criar o JSON, estender o seed (idempotente; atualizar títulos como já faz) e ligar `suggested_topic` em `occurrence_out`/`guidance_out`.
- [ ] **Step 6:** Discursiva: `essay_kind(occ)` passa a usar `essay_kind_for(slot.selection_mode, weeks_since(occ.week_start, template.effective_from))`; `_theme_state` filtra as ocorrências de discursiva por esse tipo derivado (não mais por `selection_mode == kind`). Teste em `test_guidance.py` (integração): T05 de 2026-10-30 recebe tema `complementary`; T05 de 2026-11-06, `technical_case`.
- [ ] **Step 7:** Rodar suíte da API → PASS. Commit `feat(api): add one-block-per-day cycle template`.

### Task 3: Meta semanal de minutos pelo template

**Files:**
- Modify: `apps/api/app/game/snapshot.py:91-106`
- Test: `apps/api/tests/integration/test_game.py`

**Interfaces:**
- Consumes: `select_template`, `to_input`, `templates` de `app.planning.service`.

- [ ] **Step 1:** Testes: (a) semana de 2026-10-12 com 540 min reais não fica completa; (b) semana de 2026-10-26 com 300 min reais (sessões avulsas) fica completa.
- [ ] **Step 2:** Rodar → (b) FAIL.
- [ ] **Step 3:** Em `complete_weeks`, `default_goal` = `weekly_minutes` do template vigente em `ws` (fallback `settings.weekly_goals["minutes"]` se não houver template).
- [ ] **Step 4:** PASS. Commit `feat(api): take weekly minutes goal from the active template`.

### Task 4: Até 3 revisões na missão do dia útil

**Files:**
- Modify: `apps/api/app/domain/mission.py:59-70`, `apps/api/app/game/missions.py:80-82`
- Test: `apps/api/tests/unit/test_mission.py`, `apps/api/tests/integration/test_mission.py`

**Interfaces:**
- Produces: `MAX_WEEKDAY_REVIEWS = 3`; em `build_mission`, só a 1ª revisão é `required=True`.

- [ ] **Step 1:** Unit: `build_mission` com 3 `ReviewRef` → kinds `review` com `required` `[True, False, False]`. Integração: 4 revisões vencidas em dia útil → missão com 3, a mais antiga obrigatória; concluir só a 1ª + bloco → missão completa.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar (`due_reviews(db, day)[:MAX_WEEKDAY_REVIEWS]`). Free mission inalterada.
- [ ] **Step 4:** PASS. Commit `feat(api): include up to three due reviews in the daily mission`.

### Task 5: Comando de replanejamento

**Files:**
- Create: `apps/api/app/replan.py`
- Test: `apps/api/tests/integration/test_replan.py`

**Interfaces:**
- Produces: `replan(db: Session, today: date) -> dict` (contagens: `blocks_skipped`, `reviews_rescheduled`, `reviews_created`, `reviews_dismissed`, `week_generated`) e `main()` que roda com `SessionLocal`, `clock.get_today()`, faz `commit` e imprime o dicionário. Constantes: `CUTOVER = date(2026, 10, 26)`, `SKIP_REASON = "replanejamento: 1 tópico/dia"`.
- Consumes: `ensure_week` (Task 2 já faz a semana sair do template novo).

- [ ] **Step 1: Teste do cenário real** — montar no banco de teste (via API, `clock.today` ajustado): teoria `C04.01` 10/10; `B03.01` e `E03.01` 14/10; `C03.01` 15/10; `C02.01` e `E02.01` 20/10 (ocorrências da semana 19/10 em 20/10 concluídas); depois `replan(db, date(2026, 10, 26))`. Asserções:
  - 12 ocorrências da semana 19/10 `skipped` com `SKIP_REASON`; as 3 de 20/10 seguem `completed`.
  - Pendentes por tópico: `C04.01`, `B03.01`, `E03.01` → `{1: 31/10, 7: 07/11, 21: 21/11}`; `C03.01`, `C02.01`, `E02.01` → `{1: 01/11, 7: 08/11, 21: 22/11}`.
  - Semana 26/10 gerada com `T01`–`T05`; settings conforme D7.
- [ ] **Step 2:** `test_replan_is_idempotent`: segunda chamada devolve tudo zero e o banco fica igual (Review Focus 2).
- [ ] **Step 3:** `test_replan_keeps_completed_review`: uma revisão `completed` não muda de data nem de status.
- [ ] **Step 4:** `test_replan_aborts_on_old_template_week`: semana 26/10 com ocorrência de slot do template inicial → `ApiError`/`RuntimeError` e nada gravado (Review Focus 5).
- [ ] **Step 5:** Rodar → FAIL. **Step 6:** Implementar `replan` conforme D9 (ignora o limite D4 de propósito: as âncoras já distribuem 3 por dia). **Step 7:** PASS.
- [ ] **Step 8:** Commit `feat(api): add one-off replan command for one topic per day`.

### Task 6: Interface — roteiro de 10 min e revisões bônus

**Files:**
- Modify: `apps/web/src/features/reviews/ReviewSession.tsx:15-20,51`, `apps/web/src/features/reviews/ReviewsPage.tsx:32`, `apps/web/src/features/today/TodayPage.tsx:248-256`
- Test: `apps/web/src/features/reviews/ReviewSession.test.tsx`, `apps/web/src/features/today/TodayPage.test.tsx`

- [ ] **Step 1:** Testes: `ReviewSession` mostra `Flashcards 3 min`, `5 questões CEBRASPE do tópico 5 min`, `Análise de erros sem consulta 2 min` e o registro abre com 10 min (renomear o teste de 30 min); `MissionRow` de revisão com `required: false` mostra `(bônus)` como o check-out.
- [ ] **Step 2:** `rtk proxy npx vitest run` → FAIL. **Step 3:** Implementar; texto da página de revisões: "Roteiro de 10 min: flashcards, 5 questões CEBRASPE e análise de erros. Até 3 revisões por dia."
- [ ] **Step 4:** `npx tsc --noEmit -p .` e `rtk proxy npx vitest run` → PASS. Screenshots 360px e 1280px de Hoje (missão com 3 revisões) e de uma revisão; ler com Read.
- [ ] **Step 5:** Commit `feat(web): show the ten-minute review script and bonus reviews`.

### Task 7: Docs e config

**Files:**
- Modify: `docs/02-edital-e-plano.md` §3–4, `docs/10-gamificacao-e-rotina.md` §2 (itens da missão), §6 (metas semanais, etapas) e §7 (mínimo de `specific` = 2 blocos), `docs/data/gamificacao.json` (`settings_defaults` D7, `stages` D8, `rebalance.specific_min_minutes` = 120), `README.md` (seção curta sobre `python -m app.replan`)

- [ ] **Step 1:** Editar; no §3 de `docs/02`, manter o ciclo-base antigo como histórico ("até 25/10") e adicionar o ciclo de 26/10.
- [ ] **Step 2:** Rodar suíte da API (o seed lê `gamificacao.json`) → PASS. Commit `docs: describe one topic per day routine`.

### Task 8: Aplicar no banco real (só com confirmação do usuário)

- [ ] **Step 1:** Pedir confirmação explícita para: backup, `docker compose build app && docker compose up -d app` e rodar o replan.
- [ ] **Step 2:** Backup: `docker compose exec -T db pg_dump -U cgu -Fc cgu > backups/cgu-$(date +%Y%m%d-%H%M%S)-pre-replan.dump`; conferir tamanho > 0.
- [ ] **Step 3:** `docker compose build app && docker compose up -d app` (o seed carrega o template novo); HTTP 200 em `http://127.0.0.1:8082/`.
- [ ] **Step 4:** `docker compose exec app python -m app.replan`; conferir a saída: 12 blocos dispensados, 13 reagendadas + 5 criadas, semana gerada.
- [ ] **Step 5:** Conferir no app: Hoje (26/10) com E01.01 sugerido; Revisões com 31/10 e 01/11.
