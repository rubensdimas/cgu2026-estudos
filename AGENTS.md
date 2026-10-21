# AGENTS.md

App local e de usuário único para a preparação ao concurso CGU 2026 (AFFC — Desenvolvimento de Sistemas): FastAPI + React/TS + PostgreSQL em `docker compose`. Produto e regras de negócio: `docs/01`–`docs/10`. Comandos de execução e teste: `README.md`.

## Fluxo por etapa

Escolha a skill pela etapa do pedido e anuncie em uma linha qual está em uso; o usuário não precisa digitar o comando.

| Etapa | Gatilho | Skill |
| --- | --- | --- |
| Esclarecer | pedido vago, ajuste de UI ou produto, "critique", "encontre lacunas" | `mattpocock-skills:grilling` |
| Planejar | grilling aprovado, "planeje" | `superpowers:writing-plans` |
| Implementar backend/domínio | mudança em `apps/api` | `mattpocock-skills:tdd` |
| Implementar UI | mudança em `apps/web` | `frontend-design:frontend-design` |
| Depurar | algo quebrado, falhando ou lento | `mattpocock-skills:diagnosing-bugs` |
| Revisar | branch pronta para integrar | `code-review` |
| Entregar | usuário pede PR | `mattpocock-skills:pr` |

- **Grilling**: rodadas numeradas, cada pergunta com resposta recomendada. Implemente depois que o usuário confirmar o entendimento compartilhado; "concordo" aceita todas as recomendações da rodada.
- **Plano**: salve em `docs/superpowers/plans/AAAA-MM-DD-slug.md` (spec de design em `docs/superpowers/specs/`, quando houver) e commite o plano na branch antes do código.
- **Execução**: siga o plano na própria sessão (`superpowers:executing-plans`). Subagentes só quando o usuário pedir.
- **UI**: trabalhe dentro do sistema visual existente (tema escuro, tokens em `apps/web/src/index.css`, fonte pixel reservada a destaques), validado em 360px.
- **Revisão**: correções num commit `fix: address branch review findings`.

## Autonomia

- Por conta própria: criar branch `feat/`, `fix/` ou `docs/` a partir da `main` e commitar ao fim de cada tarefa.
- Só com pedido explícito: push, PR e subir para o container.
- Preserve sempre o volume `cgu2026_pgdata`, os bancos `cgu` e `cgu_test` e a pasta `backups/`.

## Idioma

Conversa, documentos e textos da interface em pt-BR. Commits em inglês, no padrão Conventional Commits.

## Pronto

Uma tarefa está pronta quando a verificação de cada área tocada passou e o resultado foi relatado:

- `apps/web`: `npx tsc --noEmit -p .` e `npx vitest run`, dentro de `apps/web`.
- `apps/api`: `docker compose --profile test run --rm test`.
- UI: screenshots em 360px e 1280px do app rodando (`npx vite` em `apps/web` com o compose ativo; `npx playwright screenshot --viewport-size=360,1600 --full-page`).
- Container, quando pedido: `docker compose build app && docker compose up -d app`, depois confirme HTTP 200 em `http://127.0.0.1:${APP_PORT:-8082}/`.

Rodar o vitest reescreve `apps/web/.vitest/json/output.json`; deixe esse arquivo fora dos commits.
