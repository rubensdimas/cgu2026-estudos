# CGU 2026 — Plano de implementação

Versão 2.0 · 09/10/2026.

> **Para execução por agentes:** usar `superpowers:executing-plans` (ou `superpowers:subagent-driven-development`) tarefa por tarefa, com TDD nas funções puras. Parar ao fim de cada fatia para uso real e revisão.

**Objetivo:** app local gamificado, utilizável **hoje (09/10/2026)** com a rotina diária (F0+F1), e evoluído em fatias curtas até o painel completo.

**Arquitetura:** monólito FastAPI que serve o React compilado; PostgreSQL; `docker compose` no Mac; acesso pelo celular via `tailscale serve`. Regras de domínio e de jogo são funções puras em `apps/api/app/domain/`.

**Especificação:** [PRD](01-PRD.md), [edital e plano](02-edital-e-plano.md), [regras](03-regras-de-negocio.md), [domínio](04-modelo-de-dominio.md), [arquitetura](05-arquitetura-e-contratos.md), [UX](06-ux-e-fluxos.md), [gamificação](10-gamificacao-e-rotina.md).

## Restrições globais

- Usuário único, sem login; porta `127.0.0.1:8080`; remoto só via Tailscale.
- pt-BR, America/Sao_Paulo; instantes UTC; datas civis YYYY-MM-DD; “hoje” vem de `clock.today()`.
- Regras do edital `edital-2026-10-08-v1`: 40/40/90 itens, pesos 1/1/2, mínimos 8/12/54/78; discursivas 30/70 pontos, 30/60 linhas, mínimo 50; `NFC=NFPO/26+NFPD/10`.
- Ciclo: plano 09/10–11/12/2026; semana inicial parcial (S13–S15); 15 slots de 60 min; 420/180/180/120.
- Criações com UUID do cliente; edições com `version`; jogo 100% derivado.
- Sem IA, anexos, enunciados de terceiros, offline, notificações ou login no MVP.
- Dependências com versão fixada e lockfile; sem atualização por rotina.
- Não modificar nem republicar o site original.

## Calendário alvo

| Fatia | Conteúdo | Alvo |
|---|---|---|
| F0 | Fundação: repo, compose, esqueletos, tema | 09/10 |
| F1 | Rotina diária: catálogo, ciclo, sessões, missão, XP, nível, sequência, PWA | 09/10 |
| F2 | Questões, caderno de erros, metas semanais | 14/10 |
| F3 | Revisões e itens de revisão na missão | 18/10 |
| F4 | Discursivas, simulados, etapas/chefões, rebalanceamento | 22/10 (antes do chefão diagnóstico, 24–25/10) |
| F5 | Painel, conquistas, exportação/restauração | 01/11 |

Construção não pode consumir os blocos de estudo: se F1 atrasar, estudar pelos documentos e registrar depois (sessões aceitam data passada).

## Contratos puros (`apps/api/app/domain/`)

| Módulo | Assinatura | Fatia |
|---|---|---|
| `cycle.py` | `generate_week(template: TemplateInput, week_start: date, plan_starts_on: date, plan_ends_on: date) -> list[OccurrenceInput]` | F1 |
| `mission.py` | `build_mission(day: date, pending_occurrences: list[OccRef], due_reviews: list[ReviewRef], question_goal: int, suggested_topic_id: str \| None) -> list[MissionItemInput]` | F1 (reviews/questões vazios até F2/F3) |
| `mission.py` | `item_state(item: MissionItemInput, facts: DayFacts) -> Literal["pending","done","not_applicable"]` · `is_complete(items: list[tuple[bool, str]]) -> bool` | F1 |
| `xp.py` | `xp_ledger(facts: GameFacts, table: XpTable) -> list[XpEntry]` · `level_for_xp(total: int, titles: list[TitleBand]) -> LevelInfo` | F1 |
| `streak.py` | `streak_state(minutes_by_date: dict[date,int], day_offs: set[date], complete_week_ends: set[date], start: date, today: date, min_minutes: int, max_freezes: int) -> StreakState` | F1 |
| `scoring.py` | `score_batch(...) -> BatchScore` · `objective_result(batches) -> ObjectiveResult` · `final_result(objective, complementary, technical) -> FinalResult` | F2/F4 |
| `goals.py` | `weekly_goals_progress(week_start: date, facts: WeekFacts, goals: WeeklyGoals) -> list[GoalProgress]` | F2 |
| `reviews.py` | `suggest_reviews(studied_on: date, exam_on: date, offsets: list[int]) -> list[ReviewSuggestion]` | F3 |
| `stages.py` | `stage_progress(today: date, stages: list[StageDef], facts: StageFacts) -> list[StageProgress]` | F4 |
| `rebalance.py` | `suggest_rebalance(objective: ObjectiveResult, template: TemplateInput, rules: RebalanceRules) -> RebalanceSuggestion` | F4 |
| `achievements.py` | `evaluate(facts: AchievementFacts, defs: list[AchievementDef]) -> list[AchievementState]` | F5 |

Formatos: `XpEntry{date, source, ref_id, xp}`; `LevelInfo{level, title, xp_total, xp_into_level, xp_for_next}`; `StreakState{current, best, freezes_available, frozen_days: list[date], at_stake_today: bool, minutes_today: int}`; `OccurrenceInput{cycle_slot_code, week_start, planned_on, window, status="pending"}`; `BatchScore`, `ObjectiveResult`, `FinalResult` conforme v1 (R04–R06). `GameFacts` agrega sessões ativas (data, minutos, id), ocorrências concluídas (data de conclusão = `studied_on` da sessão que concluiu), missões completas e itens opcionais concluídos, lotes, erros, revisões, discursivas, simulados, semanas completas e dias de fim de semana ativos.

---

## F0 — Fundação

**Arquivos:** `docker-compose.yml`, `Dockerfile`, `.env.example`, `.gitignore`, `apps/api/{pyproject.toml,alembic.ini,migrations/,app/{main,config,db,errors,clock}.py}`, `apps/web/{package.json,vite.config.ts,tailwind.config.ts,index.html,src/main.tsx,src/app/}`, `scripts/{backup.sh,restore.sh}`, `README.md`.

- [ ] Inicializar `apps/api` com uv (FastAPI, SQLAlchemy 2, psycopg 3, Alembic, Pydantic v2, pytest) e `apps/web` com Vite React-TS (React Router, TanStack Query, Tailwind, Vitest, `@fontsource/{chakra-petch,inter,jetbrains-mono}`); fixar versões e gerar lockfiles.
- [ ] `docker-compose.yml`: `db` (postgres:17.x, volume `pgdata`, healthcheck, init cria `cgu_test`), `app` (build multi-stage, `127.0.0.1:8080:8000`, depende de `db` saudável, entrypoint `alembic upgrade head && python -m app.seed && uvicorn`), `backup` (laço diário `pg_dump -Fc` → `./backups`, retém 14).
- [ ] `main.py`: `/api/v1/health`, handler de erro padronizado com `request_id`, middleware 415 para mutações sem JSON, `/static` com fallback SPA.
- [ ] Web: tokens de cor e fontes de [06](06-ux-e-fluxos.md), layout com HUD placeholder e navegação (lateral/inferior).
- [ ] Verificar: `docker compose up -d --build` → `curl 127.0.0.1:8080/api/v1/health` = 200; página abre em tema escuro; `docker compose restart` preserva volume. Commit.

## F1 — Rotina diária (v1 de uso)

### F1.1 Catálogo, plano e ciclo

**Arquivos:** `app/catalog/*`, `app/planning/*`, `app/domain/cycle.py`, `app/seed.py`, `tests/unit/test_cycle.py`, `tests/integration/test_seed.py`.

- [ ] Teste de seed: 13 disciplinas, 68 tópicos, 1 plano (09/10–11/12), 1 template inicial `effective_from=2026-10-05`, 15 slots, 900 min, linha de `settings` com padrões de `gamificacao.json`; rodar seed 2× → mesmas contagens. Confirmar falha.
- [ ] Implementar modelos, migração e seed idempotente (upsert por código).
- [ ] Testes de `generate_week`: `week_start=2026-10-05` → 3 ocorrências (S13, S14, S15) em 09/10; `2026-10-12` → 15 ocorrências entre 12 e 16/10 com 420/180/180/120; `2026-10-13` → erro “segunda-feira obrigatória”; `2026-12-14` → erro “fora do plano”; template com `effective_from` posterior não é usado em semana anterior.
- [ ] Implementar `generate_week` e `POST /plans/current/weeks` (repetir devolve a mesma semana; unicidade slot/semana no banco); `GET /plans/current`, `GET /occurrences`, catálogo, `PUT /topics/{id}/progress`.

### F1.2 Sessões e ocorrências

**Arquivos:** `app/study/*`, `tests/integration/test_sessions.py`.

- [ ] Testes: sessão de 50 min com 2 tópicos soma 50; sessão avulsa sem ocorrência; duração 0 e 721 → 422; mesmo `id`+conteúdo → 200 e 1 registro; mesmo `id`+conteúdo diferente → 409; PATCH com versão antiga → 409; `complete_occurrence=true` conclui a ocorrência na mesma transação; excluir a única sessão devolve ocorrência a `pending`; `studied_on` é exatamente a data enviada.
- [ ] Implementar `POST/PATCH/DELETE/GET /sessions` e `PATCH /occurrences/{id}` (remanejar `planned_on/window`, `skipped` com motivo, reabrir sem apagar sessões, concluir exige sessão ativa).

### F1.3 Missão do dia

**Arquivos:** `app/domain/mission.py`, `app/game/{models,schemas,service,router}.py`, `tests/unit/test_mission.py`, `tests/integration/test_mission.py`.

- [ ] Testes unitários: sexta 09/10 com 3 ocorrências → itens block×3 obrigatórios + checkout opcional; sábado → `kind=free` sem itens automáticos; todos `not_applicable` → incompleta; 1 `done` + resto `not_applicable` → completa; ocorrência remanejada para outra data → item `not_applicable/rescheduled`.
- [ ] Testes de integração: `POST /days/2026-10-09/mission` 2× → mesma missão; data futura → 422; `GET /days/{date}` sem missão não grava; concluir ocorrência muda o item para `done` sem gravar no item.
- [ ] Implementar modelos, `GET /days/{date}`, `POST /days/{date}/mission`, `PATCH /missions/{id}/items/{item_id}`, `PUT /missions/{id}/checkout`; missão livre aceita `occurrence_ids` escolhidos (remanejados para a data na mesma transação, máx. 2).

### F1.4 XP, nível e sequência

**Arquivos:** `app/domain/{xp,streak}.py`, `app/game/service.py`, `tests/unit/{test_xp,test_level,test_streak}.py`, `tests/integration/test_game.py`.

- [ ] Testes de XP: sessão 50 min + bloco concluído + missão completa (mesmo dia) = 50+20+50 = 120; 300 min num dia → 240 de minutos; sessão excluída → 0 e bloco volta a pendente; checkout salvo em missão → +10; sábado com 45 min → 45 + 20.
- [ ] Testes de nível: 0 → Nv 1; 99 → 1; 100 → 2; 300 → 3; 15.300 → 18 “AFFC”; `xp_into_level`/`xp_for_next` coerentes.
- [ ] Testes de sequência (start 09/10, min 30): 09/10=45, 12/10=30, 13/10=0 (sem congelamento), today=14/10 → current 0, best 2; mesmo cenário com 13/10 como folga → current 2; sábado/domingo sem estudo não quebram; today com 10 min → `at_stake_today=true`, current inalterado; semana 12–16/10 completa concede congelamento que cobre 19/10 vazio; estoque nunca > 2.
- [ ] Implementar `GET /game/summary`, `GET /game/xp`, `PUT/DELETE/GET /day-offs`; incluir `game_delta` (diferença do ledger antes/depois) nas respostas de sessão, ocorrência, missão e checkout.

### F1.5 Interface da v1

**Arquivos:** `apps/web/src/features/{today,cycle,catalog,settings}/`, `src/app/Hud.tsx`, `src/shared/api/client.ts`, `public/manifest.webmanifest`, ícones.

- [ ] Cliente API: gera UUID (`crypto.randomUUID`) ao abrir o formulário e reutiliza no reenvio; trata 409/422 com mensagens de [06](06-ux-e-fluxos.md).
- [ ] HUD (nível, barra XP, sequência, congelamentos, D-n) com dados de `/game/summary`.
- [ ] Hoje: “Gerar semana” quando faltar, “Abrir o dia”, anel da missão, itens com ação (registrar sessão pré-preenchida, não se aplica, remanejar), check-out, XP do dia, toast `game_delta`, cartão de subida de nível.
- [ ] Ciclo: semana em lista por dia/janela; concluir/dispensar/remanejar. Edital: lista por prova/disciplina com estado declarado. Configurações: folgas.
- [ ] PWA: manifest (nome “CGU 2026”, `display: standalone`, tema `#0B1220`), ícones 192/512; sem service worker de cache.
- [ ] Vitest: formulário mantém dados em erro de rede; reenvio usa o mesmo `id`.

### F1.6 Verificação da v1

- [ ] `docker compose run --rm app pytest` sem falhas.
- [ ] Jornada real de 09/10: gerar semana → abrir o dia → registrar sessão S13 → ver XP e anel → reiniciar compose → dados presentes.
- [ ] `tailscale serve --bg 8080`; abrir pelo celular, instalar PWA, registrar sessão; ver no Mac.
- [ ] Teclado, foco visível, 360 px, texto a 200%, `prefers-reduced-motion`.
- [ ] Backup: forçar um `pg_dump`, restaurar em database temporária com `scripts/restore.sh` e conferir contagens. Commit e tag `v1`.

**Marco:** rotina diária utilizável. Usar por ao menos 2 dias antes de F2, anotando atritos.

---

## F2 — Questões, erros e metas semanais (alvo 14/10)

**Arquivos:** `app/domain/{scoring,goals}.py`, `app/practice/*`, `tests/unit/{test_scoring,test_goals}.py`, `tests/integration/test_practice.py`, web `features/{practice,goals}/`.

- [ ] Testes de `score_batch`: P3(6,4,0,0,10) → score 4, accuracy 0.6, net 0.2; P1(2,8,0,0,10) → −6; 10 brancos → accuracy null; soma ≠ total → erro.
- [ ] Implementar lotes e erros (CRUD, UUID do cliente, `version`, exclusão lógica junto com sessão).
- [ ] Missão: item `questions` (meta de `settings.daily_question_goal`, tópico sugerido = estudado no dia ou menor acerto com amostra ≥ 20) passa a ser gerado para missões novas.
- [ ] XP: +1/item (cap 200/dia), +10/erro (cap 100/dia), +10 item opcional de questões.
- [ ] Testes de `weekly_goals_progress`: semana inicial parcial → 180 min/3 blocos/1 missão/2 discursivas/8-8-18 itens; semana cheia padrão; sem dados → “sem registros”, não 0%.
- [ ] Telas Prática (formulário com validação de soma, histórico com amostra e rótulo “parcial”) e Metas. Commit.

## F3 — Revisões (alvo 18/10)

**Arquivos:** `app/domain/reviews.py`, `app/reviews/*`, `tests/unit/test_review_schedule.py`, `tests/integration/test_reviews.py`, web `features/reviews/`.

- [ ] Testes: estudo 12/10 → 13/10, 19/10, 02/11; estudo 01/12 → sem o de 21 dias (após 13/12); offsets negativos rejeitados; aceitar 2× não duplica; concluir não soma minutos nem cria nova cadeia; sessão excluída dispensa pendentes derivadas.
- [ ] Implementar sugestões na resposta da sessão, aceite explícito, `pending|completed|dismissed`, atraso derivado.
- [ ] Missão: itens `review` obrigatórios (até 3 vencidas, mais antigas) em missões novas.
- [ ] XP: +15 no prazo, +5 atrasada. Tela Revisões. Commit.

## F4 — Discursivas, simulados, etapas e rebalanceamento (alvo 22/10)

**Arquivos:** `app/domain/{scoring,stages,rebalance}.py`, `app/essays/*`, `app/practice/simulations.py`, `app/game/stages.py`, testes correspondentes, web `features/{essays,journey}/`.

- [ ] Discursivas: tipos fixam 30/60 linhas e 30/70 pontos; nota fora do limite → 422; linhas acima → alerta; treino de 60 min cria sessão de 60 min na mesma transação e soma 60, não 120; editar duração altera ambos.
- [ ] Simulados: `objective_result` parcial → complete false, minima null; 8+12+54 → 74, minima false; 12+12+54 → 78, minima true; `final_result` com 260 e 30+70 → NFC 20; falta nota → null. `conditions=exam_day` para o chefão da etapa 3.
- [ ] Etapas: `stage_progress` com períodos e metas de [10](10-gamificacao-e-rotina.md) §6; chefão por conclusão; marcos do concurso; XP +150 simulado, +100 chefão, +40/+60 rubrica.
- [ ] Rebalanceamento: P1 12/40, P2 20/40, P3 100/180 → folgas 0.10, 0.20, 0.256 → sugere mover 1 bloco `specific` → `basic`; `specific` nunca < 300; aceitar cria template com `effective_from` = próxima segunda não gerada.
- [ ] Telas Discursivas e Jornada. Commit.

## F5 — Painel, conquistas e portabilidade (alvo 01/11)

**Arquivos:** `app/reporting/*`, `app/domain/achievements.py`, `app/portability/*`, testes correspondentes, web `features/{progress,achievements,settings}/`.

- [ ] Painel: bloco de 60 concluído com sessão de 45 → actual 45; dois tópicos não duplicam; exclusão recalcula a semana efetiva; amostra pequena < 20 respostas válidas; sem percentuais de aprovação.
- [ ] Conquistas A01–A16 com data de desbloqueio derivada; `game_delta.achievements_unlocked`.
- [ ] Exportação `schema_version=2` (settings, plano, templates, ocorrências, missões, folgas, registros; sem dados de jogo derivados) e importação com dry-run: banco vazio → mesmas contagens; reimportar → iguais ignorados; referência inválida, schema desconhecido, > 10 MiB ou conflito → nada gravado.
- [ ] Rodar toda a suíte e os casos de [08](08-validacao-e-riscos.md); jornada completa em 360 px/desktop. Commit e tag `mvp`.

## Rastreabilidade

| Requisitos | Fatia |
|---|---|
| RF01–RF04, RF12–RF14 | F1 |
| RF05, RF06, RF15 | F2 |
| RF07 | F3 |
| RF08, RF16 | F4 |
| RF09, RF10, RF17 | F5 |
