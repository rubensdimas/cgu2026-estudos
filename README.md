# CGU 2026 — Assistente de estudos gamificado

Versão 2.0 · 09/10/2026 · pt-BR · America/Sao_Paulo.

App pessoal e local de preparação para **Auditor Federal de Finanças e Controle — TI — Desenvolvimento de Sistemas (Cargo 4)**, prova em 13/12/2026. Responde todo dia: **o que estudar agora, o que foi feito, o que revisar e se a rotina está em dia**, com missão diária, XP, nível, sequência, metas e etapas com chefões.

Estado atual: especificação v2.0 pronta; plano executável de F0+F1 em [docs/superpowers/plans/2026-10-09-f0-f1-rotina-diaria.md](docs/superpowers/plans/2026-10-09-f0-f1-rotina-diaria.md); código ainda não iniciado.

## Documentos

| Arquivo | Uso |
|---|---|
| [docs/01-PRD.md](docs/01-PRD.md) | Problema, usuário, requisitos por fatia, decisões v2.0 |
| [docs/02-edital-e-plano.md](docs/02-edital-e-plano.md) | Regras do edital, catálogo, ciclo, etapas |
| [docs/03-regras-de-negocio.md](docs/03-regras-de-negocio.md) | Regras R01–R15 |
| [docs/04-modelo-de-dominio.md](docs/04-modelo-de-dominio.md) | Entidades, valores derivados, invariantes |
| [docs/05-arquitetura-e-contratos.md](docs/05-arquitetura-e-contratos.md) | Compose, módulos, API, segurança |
| [docs/06-ux-e-fluxos.md](docs/06-ux-e-fluxos.md) | Tema escuro, tipografia, telas, jornadas |
| [docs/07-plano-de-implementacao.md](docs/07-plano-de-implementacao.md) | Fatias F0–F5 com testes e alvos |
| [docs/08-validacao-e-riscos.md](docs/08-validacao-e-riscos.md) | Casos críticos, riscos, definição de pronto |
| [docs/09-orientacoes-para-implementacao.md](docs/09-orientacoes-para-implementacao.md) | Pedido pronto para agente/desenvolvedor |
| [docs/10-gamificacao-e-rotina.md](docs/10-gamificacao-e-rotina.md) | Missão, XP, nível, sequência, metas, chefões, conquistas |
| [docs/data/catalogo-edital.json](docs/data/catalogo-edital.json) | 13 disciplinas, 68 tópicos macro |
| [docs/data/ciclo-inicial.json](docs/data/ciclo-inicial.json) | Regras da prova e 15 blocos; início 09/10 |
| [docs/data/gamificacao.json](docs/data/gamificacao.json) | Metas, tabela de XP, níveis, etapas, marcos, conquistas |
| [docs/edital.pdf](docs/edital.pdf) | Edital CGU nº 1, de 08/10/2026 (fonte oficial usada) |

## Fontes

- Edital CGU nº 1, de 8 de outubro de 2026 — `docs/edital.pdf`, SHA-256 `869d4a424d4cfdb83b7de7023d82bac99944b7c95b8a894686983f2b5d32aee7` (conferido em 09/10/2026). [DOU](https://www.in.gov.br/web/dou/-/edital-cgu-n-1-de-8-de-outubro-de-2026-737675154) · [Cebraspe](https://www.cebraspe.org.br/concursos/cgu_26_affc).
- Nenhuma retificação localizada em 09/10/2026; repetir a verificação antes de cada etapa.
- [Página original do plano](https://cgu-desenvolvimento-rubens.tartcedar32.chatgpt.site): referência de conteúdo e paleta; não é alterada.

Carga horária, ciclo, metas, XP e etapas são **propostas de produto**, não determinações da banca.

## Como rodar (após F0)

```bash
cp .env.example .env          # definir POSTGRES_PASSWORD
docker compose up -d --build  # app em http://127.0.0.1:8080
tailscale serve --bg 8080     # opcional: acesso pelo celular dentro da tailnet
```

Backups diários em `./backups` (14 cópias). Restaurar: `scripts/restore.sh <arquivo>`.

## Changelog

### 2.0 — 09/10/2026

- **Gamificação** passa a integrar o produto como camada derivada centrada na rotina diária: missão do dia, XP, nível, sequência com congelamentos e folgas, metas semanais, etapas com chefões, conquistas e rebalanceamento após diagnóstico (novo `docs/10`, novo `gamificacao.json`, R13–R15).
- **Sem login, uso local**: removidos RF11, `User`/`user_id`, CSRF e recibos de idempotência; criação com UUID do cliente.
- **Stack confirmada**: FastAPI + React/TS + PostgreSQL em `docker compose` no Mac, acesso pelo celular via Tailscale, PWA instalável.
- **Monorepo** nesta pasta; documentos movidos para `docs/`, dados para `docs/data/`.
- **Ciclo inicia hoje (09/10)** com semana parcial; etapas reajustadas para incluir fins de semana.
- **Plano de implementação** reorganizado em fatias F0–F5 com alvo de uso no mesmo dia.
- **Visual**: tema escuro; Chakra Petch, Inter, JetBrains Mono.

### 1.0 — 09/10/2026

Especificação inicial: MVP sem gamificação, multi-dispositivo com login, stack proposta não confirmada.
