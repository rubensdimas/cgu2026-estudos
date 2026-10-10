# Orientações para iniciar com um desenvolvedor ou agente

Versão 2.0 · 09/10/2026.

## Pedido de implementação sugerido

> Leia o README, depois `docs/01` a `docs/10`. Implemente F0 e F1 de `docs/07-plano-de-implementacao.md` neste monorepo, com FastAPI + React/TS + PostgreSQL em `docker compose`, sem login. Use TDD nas funções puras de `apps/api/app/domain/`. Antes de escrever código, aponte divergências entre os documentos e o ambiente (Docker, Node, Python, Tailscale disponíveis no Mac). Não adicione IA, login, integrações, banco de enunciados ou funcionalidades de fatias posteriores. Rode os testes e a verificação F1.6 e informe os resultados. Pare ao entregar a rotina diária utilizável.

## Instruções de produto

- Preparação pessoal de Rubens para AFFC — Desenvolvimento de Sistemas; app local, usuário único, não é SaaS.
- A gamificação sustenta a rotina diária (missão, sequência, metas); é derivada e nunca recompensa acerto.
- Regras oficiais vêm de `docs/edital.pdf` (versão `edital-2026-10-08-v1`); não assumir equivalência com concursos anteriores.
- 15 h/semana são meta; não criar histórico de horas realizadas nem dados de exemplo no banco real.
- Distinguir planejamento, realização, cobertura, resultado e XP.
- Não tratar mínimos, autoavaliação, nível ou XP como classificação ou preparo.

## Ordem de decisões

1. Confirmar ferramentas locais (Docker Desktop/OrbStack, uv, Node LTS, Tailscale).
2. Fixar versões e gerar lockfiles na inicialização.
3. F0 → F1 → uso real por 2 dias → F2 → F3 → F4 (antes de 24/10) → F5.

## Condições para propor mudança

Apresentar impacto e atualizar documentos antes de trocar stack, ampliar escopo, alterar esquema do catálogo, mudar cálculo oficial ou valores de jogo, ou expor o app fora da tailnet (exige identidade). Não expandir a entrega porque uma biblioteca facilita algo não pedido.

## Entrega esperada por fatia

Código, migração, testes do comportamento crítico, resumo do que funciona e do que está limitado. Não declarar finalização só por compilar: demonstrar persistência após reiniciar o compose e acesso pelo celular.
