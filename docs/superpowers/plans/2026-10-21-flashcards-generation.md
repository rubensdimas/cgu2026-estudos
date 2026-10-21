# Flashcards gerados por IA (Parte 1) — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerar com a OpenAI, a partir de uma sessão de teoria, de 5 a 10 flashcards presos aos subitens do edital do tópico, revisá-los como rascunho e manter um baralho de cartões aprovados.

**Architecture:** Novo pacote `apps/api/app/flashcards/` com três camadas: `domain.py` (puro: monta a entrada do modelo e filtra a saída), `ai.py` (adaptador da OpenAI atrás de um `Protocol`, injetado por dependência do FastAPI e trocado por um falso nos testes) e `service.py`/`router.py` (persistência e HTTP). No front, `features/flashcards/` com o painel de geração/rascunho, usado em Hoje e na página nova `/cartoes`.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, SDK `openai` (Responses API, saída estruturada `json_schema` strict), pytest; React + TanStack Query + vitest.

**Spec:** entendimento compartilhado do grilling desta conversa (Parte 1), resumido em "Regras".

## Regras (spec)

- Só sessões **ativas de teoria com tópico** geram. Botão também para sessões passadas.
- Entrada do modelo: disciplina, tópico, subitens do edital numerados (`docs/data/orientacoes.json` → `subitens[topic]`), materiais sugeridos (título + nota, quando houver) e o texto "O que estudei / errei" (pré-preenchido com `session.notes`, opcional). O modelo não abre links.
- Saída: de 5 a 10 cartões; cada um com `categoria`, `subitem`, `frente`, `verso`; mais `origem`, `foco`, `prioridades` (até 3). Cartão com `subitem` fora da lista enviada é descartado; acima de 10, corta.
- Prompt: banca CEBRASPE, terminologia do edital, nada fora dos subitens, nada de artigo/lei inventado; sem quantidade forçada.
- Rascunho: aprovar, editar frente/verso, descartar, "Aprovar todos". "Gerar novamente" apaga só os rascunhos da sessão; aprovados ficam.
- Sem chave: botão desabilitado com explicação. Falha/timeout (60 s): mensagem + "Tentar novamente", nada gravado.
- Modelo padrão `gpt-6.1-sol`, configurável em `OPENAI_MODEL`; chave em `OPENAI_API_KEY`, só no container `app`, nunca no front nem em log.

## Global Constraints

- Textos de interface e docs em pt-BR; commits em inglês (Conventional Commits) terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Preservar volume `cgu2026_pgdata`, bancos `cgu`/`cgu_test`, pasta `backups/`. Sem push, PR ou deploy sem pedido.
- `apps/web/.vitest/json/output.json` fora dos commits.
- Testes nunca chamam a OpenAI: a dependência `get_generator` é sobrescrita por um falso.
- UI no sistema visual existente (tokens em `apps/web/src/index.css`), validada em 360px e 1280px.

## Review Focus

1. Modelo devolve `subitem` com formato diferente (`"1.2."`, `"Subitem 1.2"`) → normalizar antes de validar, não descartar tudo (teste em Task 1).
2. Resposta da OpenAI recusada (`refusal`) ou JSON inválido → erro 502 `ai_failed`, nada gravado (teste em Task 3 com falso que lança).
3. Gerar novamente com cartões já aprovados → aprovados intactos, rascunhos substituídos (teste em Task 3).
4. Sessão excluída depois da geração → os cartões aprovados continuam no baralho; gerar de novo nela dá 404 (teste em Task 3).
5. Texto "O que estudei" longo (até 2000) e aspas/quebras de linha → enviado intacto; limite validado com 422 acima de 4000 (teste em Task 3).

---

### Task 1: Domínio puro e prompt

**Files:**
- Create: `apps/api/app/flashcards/__init__.py`, `apps/api/app/flashcards/domain.py`, `apps/api/app/flashcards/prompt.md`
- Modify: `docs/instrucao_gerador_flashcards.md` (vira um parágrafo apontando para o prompt e explicando a adaptação)
- Test: `apps/api/tests/unit/test_flashcards_domain.py`

**Interfaces:**
- Produces:
  - `CATEGORIES = ("conceito", "distincao", "condicao", "causa_consequencia", "aplicacao", "erro_recorrente", "fundamentacao")`
  - `@dataclass(frozen=True) class Context: subject: str; topic_id: str; topic: str; subitems: list[str]; materials: list[dict]; studied: str`
  - `@dataclass(frozen=True) class Card: category: str; subitem: str; front: str; back: str`
  - `@dataclass(frozen=True) class Batch: origin: str; focus: str; priorities: list[str]; cards: list[Card]`
  - `subitem_code(text: str) -> str` — primeiro token numérico de um subitem (`"1.2 Distinção…"` → `"1.2"`).
  - `user_input(ctx: Context) -> str` — texto em pt-BR com seções "Disciplina", "Tópico", "Subitens do edital (use apenas estes)", "Materiais sugeridos" (omitida se vazia), "O que estudei / errei" (ou "Não informado — use apenas os subitens e indique origem 'tópico informado'").
  - `OUTPUT_SCHEMA: dict` — JSON schema strict: `{origem: str, foco: str, prioridades: str[], cards: [{categoria: enum CATEGORIES, subitem: str, frente: str, verso: str}]}`.
  - `parse_batch(raw: dict, ctx: Context) -> Batch` — normaliza `subitem` (remove prefixo não numérico e ponto final), descarta cartões com subitem fora de `ctx`, frente/verso vazios ou categoria inválida; corta em 10; `prioridades` cortadas em 3.
  - `load_prompt() -> str` — lê `prompt.md` ao lado do módulo (`lru_cache`).

- [ ] **Step 1: Testes falhando**
  - `test_subitem_code_takes_leading_number`: `"1.2 Distinção…"` → `"1.2"`.
  - `test_user_input_lists_subitems_and_omits_empty_materials`: contém `"1.1 Transparência"` e `"1.2 Distinção"`; sem `"Materiais sugeridos"` quando `materials=[]`; com `studied=""` contém `"Não informado"`.
  - `test_parse_batch_keeps_valid_and_drops_out_of_scope`: subitens `1.1`/`1.2`; cartões com subitem `"1.2."`, `"Subitem 1.1"`, `"3.4"`, frente vazia → mantém 2 com subitens `"1.2"` e `"1.1"`.
  - `test_parse_batch_caps_at_ten_cards_and_three_priorities`: 12 cartões válidos e 5 prioridades → 10 e 3.
  - `test_prompt_mentions_cebraspe_and_scope`: `load_prompt()` contém `"CEBRASPE"` e `"subitens"`.

- [ ] **Step 2: Rodar** `cd apps/api && uv run pytest tests/unit/test_flashcards_domain.py -q` — Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementar `domain.py` e escrever `prompt.md`.** O prompt mantém as seções 1, 2, 4, 5 e 6 da instrução original, com estas mudanças: escopo restrito aos subitens recebidos (cada cartão cita o seu); "gere de 5 a 10 cartões, menos se o conteúdo não sustentar; nenhum se nada for fiel"; seção 2 sem "conversa atual" (a entrada é o texto do usuário); remove seções 3, 7, 8, 9; categorias com as chaves de `CATEGORIES`; `origem` descreve a fonte ("observação da sessão + subitens" ou "tópico informado"); `prioridades` só com dados do texto do usuário, senão lista vazia.

- [ ] **Step 4: Rodar** (mesmo comando) — Expected: PASS.

- [ ] **Step 5: Commit** — `feat(api): add flashcard prompt and output parsing`

### Task 2: Modelo de dados, configuração e adaptador OpenAI

**Files:**
- Modify: `apps/api/app/models.py`, `apps/api/app/config.py`, `apps/api/pyproject.toml` + `uv.lock` (`openai`), `docker-compose.yml` (serviço `app`), `.env.example`, `.env` (renomear `API_KEY` → `OPENAI_API_KEY`, sem ler/imprimir o valor)
- Create: `apps/api/app/flashcards/ai.py`, `apps/api/migrations/versions/20261021_<rev>_flashcards.py` (`down_revision = "8d4b2e6f1a90"`)
- Test: `apps/api/tests/unit/test_flashcards_ai.py`

**Interfaces:**
- Produces:
  - `FlashcardBatch(Base)` tabela `flashcard_batches`: `session_id` (PK, FK `study_sessions.id`), `model: str`, `studied: Text`, `origin: Text`, `focus: Text`, `priorities: JSONB list`, `created_at`.
  - `Flashcard(Versioned, Base)` tabela `flashcards`: `id: Uuid PK`, `session_id: FK study_sessions.id (index)`, `topic_id: FK topics.id (index)`, `subitem: String(16)`, `category: String(24)`, `front: Text`, `back: Text`, `status: String(16)` com check `status in ('draft','approved')`, check de `category` com `CATEGORIES`.
  - `config.OPENAI_API_KEY: str` (vazio = desligado), `config.OPENAI_MODEL: str` (padrão `"gpt-6.1-sol"`), `config.OPENAI_TIMEOUT = 60`.
  - `class AiError(Exception)`.
  - `class Generator(Protocol): model: str; def __call__(self, ctx: Context) -> Batch`.
  - `class OpenAiGenerator` — `__init__(api_key: str, model: str, client=None)`; chama `client.responses.create(model=…, instructions=load_prompt(), input=user_input(ctx), text={"format": {"type": "json_schema", "name": "flashcards", "strict": True, "schema": OUTPUT_SCHEMA}}, timeout=60)`, lê `response.output_text`, `json.loads`, `parse_batch`. Qualquer exceção do SDK, recusa ou JSON inválido vira `AiError`. Nunca loga a chave.
  - `get_generator() -> Generator | None` — `None` se `OPENAI_API_KEY` vazio.

- [ ] **Step 1: Testes falhando** (cliente falso com `responses.create` gravando os kwargs)
  - `test_openai_generator_sends_schema_prompt_and_model`: kwargs têm `model == "m"`, `text.format.strict is True`, `instructions` contém `"CEBRASPE"`, `input` contém o tópico; retorna `Batch` com os cartões válidos.
  - `test_openai_generator_wraps_failures`: cliente que lança `RuntimeError` → `AiError`; `output_text = "não é json"` → `AiError`.
  - `test_get_generator_is_none_without_key` (monkeypatch `config.OPENAI_API_KEY = ""`).
- [ ] **Step 2: Rodar** `cd apps/api && uv run pytest tests/unit/test_flashcards_ai.py -q` — Expected: FAIL.
- [ ] **Step 3: Implementar** `uv add openai`, modelos, config, `ai.py`, migração (Alembic autogenerate revisado à mão), `docker-compose.yml` → em `app.environment`: `OPENAI_API_KEY: ${OPENAI_API_KEY:-}` e `OPENAI_MODEL: ${OPENAI_MODEL:-gpt-6.1-sol}`; `.env.example` ganha `OPENAI_API_KEY=` e `OPENAI_MODEL=gpt-6.1-sol`; no `.env`, `sed -i '' 's/^API_KEY=/OPENAI_API_KEY=/' .env`.
- [ ] **Step 4: Rodar** unitários e a suíte: `docker compose --profile test run --rm test` — Expected: PASS (as tabelas novas são criadas pelo `create_all` dos testes).
- [ ] **Step 5: Commit** — `feat(api): add flashcard storage and OpenAI generator` (o `.env` não é versionado).

### Task 3: Serviço e rotas

**Files:**
- Create: `apps/api/app/flashcards/service.py`, `apps/api/app/flashcards/router.py`
- Modify: `apps/api/app/main.py` (incluir o router)
- Test: `apps/api/tests/integration/test_flashcards.py`

**Interfaces:**
- Consumes: `Context`, `Batch`, `Generator`, `AiError`, `get_generator` (Tasks 1–2); `content.guidance()` para `subitens`/`materiais`.
- Produces (prefixo `/api/v1`):
  - `GET /flashcards/status` → `{"enabled": bool, "model": str}`.
  - `GET /flashcards/sessions?from&to` → `{"items": [{"session": session_out, "drafts": int, "approved": int, "generated": bool}], "total"}` só para sessões ativas de teoria com tópico, mais recentes primeiro.
  - `GET /sessions/{id}/flashcards` → `{"batch": {model, studied, origin, focus, priorities, created_at} | null, "cards": [card_out]}`; `card_out = {id, version, session_id, topic_id, subitem, category, front, back, status}`.
  - `POST /sessions/{id}/flashcards` corpo `{"studied": str (max 4000)}` → 201 com o mesmo formato. Erros: 404 `not_found` (sessão inexistente/excluída); 422 `not_theory` ("Flashcards só para sessões de teoria com tópico."); 503 `ai_disabled` ("Configure OPENAI_API_KEY para gerar flashcards."); 502 `ai_failed` ("Não foi possível gerar agora. Tente novamente."). Usa o primeiro tópico da sessão. Substitui rascunhos e o `FlashcardBatch` da sessão; aprovados ficam.
  - `PATCH /flashcards/{id}` `{version, front?, back?, status?: "approved"}` → `card_out`; 409 `version_conflict` como nos demais.
  - `DELETE /flashcards/{id}` → 204 (rascunho ou aprovado).
  - `POST /sessions/{id}/flashcards/approve` → aprova todos os rascunhos; retorna o formato do GET.
  - `GET /flashcards?topic_id=` → `{"items": [card_out], "total"}` só aprovados, por `topic_id`, `created_at`.

- [ ] **Step 1: Testes falhando** (fixture sobrescreve `get_generator` com um falso que devolve 3 cartões em `1.1`/`1.2` e grava o `Context` recebido)
  - `test_generate_creates_drafts_with_edital_context`: sessão de teoria C02.01 com notes "LAI" → 201, 3 rascunhos; o `Context` recebido tem `subitems` de C02.01, 2 materiais e `studied == "LAI e recursos"` (corpo enviado).
  - `test_generate_rejects_non_theory_and_missing_key`: sessão de questões → 422 `not_theory`; gerador `None` → 503 `ai_disabled`; `GET /flashcards/status` → `enabled: false`.
  - `test_ai_failure_saves_nothing`: falso lança `AiError` → 502 `ai_failed`; GET da sessão → `batch: null`, `cards: []`.
  - `test_regenerate_replaces_drafts_keeps_approved`: gerar, aprovar 1 via PATCH, gerar de novo → 1 aprovado original + 3 rascunhos novos.
  - `test_edit_approve_all_discard_and_deck`: PATCH edita frente; `DELETE` um rascunho; `approve` → restantes aprovados; `GET /flashcards?topic_id=C02.01` lista 2; PATCH com versão velha → 409.
  - `test_deleted_session_keeps_deck_and_blocks_generation`: aprovar, excluir a sessão → deck mantém; POST na sessão → 404.
  - `test_studied_text_limits`: 2000 caracteres com aspas e quebras chegam intactos ao `Context`; 4001 → 422.
  - `test_sessions_listing_counts`: duas sessões de teoria (uma gerada) e uma de questões → 2 itens com `generated`/`drafts`/`approved` corretos.
- [ ] **Step 2: Rodar** `docker compose --profile test run --rm test pytest -q -p no:cacheprovider tests/integration/test_flashcards.py` — Expected: FAIL (404 nas rotas).
- [ ] **Step 3: Implementar** serviço e rotas; commit da transação no router como em `catalog/router.py`; a chamada ao modelo acontece antes de qualquer escrita.
- [ ] **Step 4: Rodar a suíte completa da API** — Expected: PASS.
- [ ] **Step 5: Commit** — `feat(api): add flashcard generation and review endpoints`

### Task 4: Painel de geração e rascunho (web)

**Files:**
- Create: `apps/web/src/features/flashcards/FlashcardPanel.tsx`, `apps/web/src/features/flashcards/FlashcardPanel.test.tsx`
- Modify: `apps/web/src/shared/api/types.ts` (`Flashcard`, `FlashcardBatch`, `SessionFlashcards`, `FlashcardSessionItem`, `FlashcardStatus`), `apps/web/src/shared/api/hooks.ts`, `apps/web/src/features/today/TodayPage.tsx` (`TodaySessions`)

**Interfaces:**
- Consumes: rotas da Task 3.
- Produces:
  - Hooks: `useFlashcardStatus()`, `useSessionFlashcards(sessionId)`, `useGenerateFlashcards()` (`{sessionId, studied}`), `usePatchFlashcard()`, `useDeleteFlashcard()`, `useApproveFlashcards()` (`sessionId`), `useFlashcardSessions(from, to)`, `useDeck(topicId?)`. Mutações invalidam `['flashcards']` (prefixo comum das query keys: `['flashcards', …]`).
  - `<FlashcardPanel session={Session} />`: textarea "O que estudei / errei" (pré-preenchida com `session.notes`, `maxLength=4000`); botão "Gerar flashcards" ou "Gerar novamente" (quando já há batch), desabilitado com o texto "Configure OPENAI_API_KEY no .env para gerar flashcards." se `enabled` falso; estado "Gerando…" e `role="alert"` com a mensagem do erro + "Tentar novamente"; `origem`/`foco` do batch; lista de cartões com categoria, subitem (`Subitem 1.2`), frente, verso; em rascunho: "Aprovar", "Editar" (frente/verso em textareas + "Salvar"), "Descartar"; "Aprovar todos" quando houver rascunhos; aprovados marcados como "Aprovado".
  - `TodaySessions`: sessões de teoria com tópico ganham botão "Flashcards" que alterna o painel abaixo da linha.

- [ ] **Step 1: Testes falhando** (`fetch` stubado como em `SessionForm.test.tsx`)
  - `gera com o texto informado e mostra os rascunhos com subitem`: digita no textarea, clica "Gerar flashcards" → corpo do POST tem `studied`; aparecem frente, verso e `Subitem 1.2`.
  - `desabilita a geração sem chave`: status `enabled: false` → botão desabilitado e texto da chave visível.
  - `mostra erro e permite tentar de novo`: POST 502 → alerta "Não foi possível gerar agora. Tente novamente." e botão "Tentar novamente" refaz o POST.
  - `aprovar todos envia a ação da sessão`: clica "Aprovar todos" → POST `/sessions/{id}/flashcards/approve`.
- [ ] **Step 2: Rodar** `rtk proxy npx vitest run src/features/flashcards` em `apps/web` — Expected: FAIL.
- [ ] **Step 3: Implementar** tipos, hooks, painel e botão em `TodaySessions` (Skill `frontend-design:frontend-design` para o painel, dentro dos tokens existentes).
- [ ] **Step 4: Verificar** `npx tsc --noEmit -p .` e `rtk proxy npx vitest run` — Expected: PASS.
- [ ] **Step 5: Commit** — `feat(web): generate and review flashcards from a theory session`

### Task 5: Página Cartões, navegação e docs

**Files:**
- Create: `apps/web/src/features/flashcards/FlashcardsPage.tsx`, `apps/web/src/features/flashcards/FlashcardsPage.test.tsx`
- Modify: `apps/web/src/app/App.tsx` (rota `/cartoes`, item "Cartões" com ícone `Layers` do `lucide-react`, entre Edital e Progresso), `docs/03-regras-de-negocio.md` (nova regra R13 — Flashcards), `docs/05-arquitetura-e-contratos.md` (tabela de rotas), `docs/01-PRD.md` (nota de IA: geração de flashcards já no MVP, sempre revisada pelo usuário), `README.md` (variáveis `OPENAI_API_KEY`/`OPENAI_MODEL`)

**Interfaces:**
- Consumes: hooks e `FlashcardPanel` (Task 4).
- Produces: `<FlashcardsPage />` com duas seções:
  - "Sessões de teoria" (últimos 30 dias até hoje): cada item mostra data, tópico, e "Sem cartões" / "N rascunhos" / "N aprovados"; botão "Flashcards" abre o `FlashcardPanel` da sessão.
  - "Baralho": cartões aprovados agrupados por tópico (`<details>` como no Edital, com contagem), cada cartão com frente visível e verso atrás de "Mostrar verso"; "Excluir" com `confirm`.

- [ ] **Step 1: Testes falhando**
  - `lista sessões de teoria com estado dos cartões`: duas sessões (uma com 2 aprovados) → textos "Sem cartões" e "2 aprovados".
  - `agrupa o baralho por tópico e revela o verso`: clica "Mostrar verso" → verso visível.
  - `App` mostra o item de navegação "Cartões` (ajustar `App.test.tsx`).
- [ ] **Step 2: Rodar** `rtk proxy npx vitest run src/features/flashcards src/app` — Expected: FAIL.
- [ ] **Step 3: Implementar** página, rota, item de navegação e docs. A barra inferior passa a ter 6 itens; o rótulo curto "Cartões" mantém a largura em 360px (a Parte 2 introduz o menu "Mais").
- [ ] **Step 4: Verificar** `npx tsc --noEmit -p .`, `rtk proxy npx vitest run`, `docker compose --profile test run --rm test` — Expected: PASS.
- [ ] **Step 5: Screenshots** em 360px e 1280px de `/` (com o painel aberto numa sessão de teoria) e `/cartoes`, com `npx vite` e o compose ativo; ler com a ferramenta Read e corrigir quebras na barra inferior antes de seguir.
- [ ] **Step 6: Teste real com a OpenAI (uma chamada paga, ~US$ 0,03)**: no container de teste, com `-e OPENAI_API_KEY` vindo do `.env`, rodar um script do scratchpad que monta o `Context` de C02.01 (subitens e materiais do `orientacoes.json`, `studied="LAI: transparência ativa e passiva, prazos de pedido e recurso"`) e chama `OpenAiGenerator`. Expected: 5 a 10 cartões, todos com subitem `1.1` ou `1.2`, em pt-BR, sem assunto fora do tópico. Registrar contagem e tokens no ledger; ler os cartões e relatar a qualidade ao usuário.
- [ ] **Step 7: Commit** — `feat(web): add flashcards page and navigation` e `docs: describe AI flashcard generation`.
