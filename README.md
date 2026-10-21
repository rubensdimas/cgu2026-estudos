# CGU 2026 — Assistente de estudos gamificado

Versão 2.0 · 09/10/2026 · pt-BR · America/Sao_Paulo.

App pessoal e local de preparação para **Auditor Federal de Finanças e Controle — TI — Desenvolvimento de Sistemas (Cargo 4)**, prova em 13/12/2026. Responde todo dia: **o que estudar agora, o que foi feito, o que revisar e se a rotina está em dia**, com missão diária, XP, nível, sequência, metas e etapas com chefões.

Estado atual: especificação v2.0 pronta; plano executável de F0+F1 em [docs/superpowers/plans/2026-10-09-f0-f1-rotina-diaria.md](docs/superpowers/plans/2026-10-09-f0-f1-rotina-diaria.md); v1 (F0+F1) implementada na branch `feat/v1-rotina-diaria`.

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

## Como rodar

Depois de clonar o projeto, crie o `.env` e configure a senha do PostgreSQL. Para iniciar o app localmente:

```bash
cp .env.example .env
# edite .env e defina POSTGRES_PASSWORD
./scripts/start-local.sh                      # app em http://127.0.0.1:8082
```

Para restaurar um backup em outra máquina, coloque o arquivo `.dump` em `BACKUP_DIR` no `.env` (padrão: `./backups/`) e execute `./scripts/start-local.sh --restore`. O script escolhe o arquivo `cgu-*.dump` mais recente e informa o erro antes de iniciar serviços se não encontrar nenhum. A restauração só ocorre em um banco vazio; se o banco já tiver tabelas, o script cancela para preservar os dados. Depois de restaurar, ele inicia o app normalmente.

Para coexistir com outros projetos, escolha uma porta TCP livre em `APP_PORT` no `.env` da raiz (por exemplo, `APP_PORT=18082`). Ausente ou vazia usa `8082`; a variável do terminal tem precedência, inclusive vazia. O app fica acessível somente em `127.0.0.1`. Cada projeto mantém seu PostgreSQL; este usa `db:5432` apenas entre containers, sem porta no host. O projeto Compose `cgu2026`, o volume existente `cgu2026_pgdata`, os bancos `cgu` e `cgu_test` e os backups são preservados.

Para desenvolver o frontend com recarga automática, mantenha o Compose ativo e execute:

```bash
cd apps/web
npm run dev
```

O proxy `/api` do Vite usa a mesma `APP_PORT` do `.env` da raiz, mesmo iniciado em `apps/web`, com a mesma precedência do terminal e padrão `8082`. Use o mesmo override nos dois comandos se configurar a porta pelo terminal. Depois de mudar a porta, reinicie o Vite e recrie o app com `docker compose up -d app` na raiz. A leitura dessa configuração não disponibiliza a senha do banco ao frontend; o build de produção também funciona sem `.env`, inclusive no Docker.

Testes:

```bash
docker compose --profile test run --rm test   # API: unitários + integração (banco cgu_test)
cd apps/api && uv run pytest tests/unit       # só unitários, sem banco
cd apps/web && npm test                       # frontend
python3 -m unittest discover -s tests/ops -p test_compose.py -v   # configuração Compose, na raiz, sem subir containers
python3 -m unittest tests.ops.test_start_local -v                   # fluxo do script local, com Docker simulado
```

Teste de arranque, na raiz, com Docker ativo e a imagem atual construída:

```bash
docker compose build app
python3 -m unittest discover -s tests/ops -p test_startup.py -v
```

Esse teste sobe PostgreSQL descartável em memória, com projeto/rede exclusivos e senha fictícia, sem acessar os bancos ou volumes existentes. Reproduz a revisão `5c9e1f3a7b21` já aplicada e verifica o arranque normal da imagem, a saúde HTTP e o catálogo persistido. Os containers temporários são removidos ao terminar. `CGU_STARTUP_IMAGE` permite escolher outra imagem runtime local.

Flashcards por IA (R16): defina `OPENAI_API_KEY` no `.env` (só o container `app` a recebe) e, opcionalmente, `OPENAI_MODEL` (padrão `gpt-6.1-sol`). Sem chave, o botão "Gerar flashcards" fica desligado. Depois de mudar o `.env`, rode `docker compose up -d app`.

Backups: um `pg_dump` ao subir e a cada 24 h em `./backups` (ou `BACKUP_DIR`), mantendo 14 arquivos. Ensaiar a restauração sem tocar no banco principal: `scripts/restore-check.sh backups/<arquivo>.dump`.

Celular: instalar o Tailscale no Mac e no celular (mesma conta), rodar `tailscale serve --bg 8082` (ou a porta escolhida em `APP_PORT`), acrescentar o nome `*.ts.net` mostrado por `tailscale serve status` em `ALLOWED_HOSTS` no `.env` e executar `docker compose up -d app`. Abrir o endereço no celular e usar “Adicionar à tela de início”. Nunca usar `tailscale funnel`: o app não tem login. O Mac precisa estar ligado para o celular acessar.

## Changelog

### 2.1 — 10/10/2026

- Identidade visual BeroLab: grafite, roxo `#b78cf2`, dourado `#f2c94f`; Inter, Fira Mono e Departure Mono.
- shadcn adotado (tokens semânticos) e componentes do Trophy UI em pt-BR.
- Nova tela Progresso: sequência com calendário (dias neutros), XP acumulado e trilha de níveis; diálogo de subida de nível.
- API: `GET /game/calendar`, níveis em `/game/config`, `level_title` no `game_delta`.

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
