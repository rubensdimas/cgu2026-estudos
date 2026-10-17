# Containers em coexistência local — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Executar este projeto ao lado dos demais, com app em porta configurável e PostgreSQL próprio preservado e acessível somente pelos containers.

**Architecture:** Preservar o namespace e a persistência atuais do Compose; parametrizar somente a porta publicada do app. Fazer o Vite consumir a mesma `APP_PORT` da raiz, com precedência do terminal e fallback `8082`, sem expor segredos ao frontend. Implementar em ciclos TDD verticais com `mattpocock-skills:tdd`, após a confirmação das duas fronteiras propostas.

**Tech Stack:** Docker Compose v2, PostgreSQL 17.6, Node 24, Vite/Vitest e TypeScript existentes; Python 3 com `unittest` e `subprocess` da biblioteca padrão para testar a CLI do Compose.

**Spec:** [Desenho confirmado](../specs/2026-10-17-containers-coexistencia-local-design.md).

## Global Constraints

- Desenvolvimento local, uma instância deste projeto coexistindo com projetos diferentes.
- Cada projeto tem seu próprio PostgreSQL. Este banco é acessível somente pelos containers, em `db:5432`, sem publicação de porta no host.
- Preservar o projeto Compose `cgu2026`, o volume existente `cgu2026_pgdata`, seus dados, o banco `cgu`, o banco de testes `cgu_test` e os backups.
- A aplicação publica `127.0.0.1:${APP_PORT:-8082}:8000`.
- `APP_PORT` é opcional: ausente ou vazio significa `8082`; um valor configurado é uma porta TCP decimal válida. A variável do terminal tem precedência sobre o `.env` da raiz.
- Manter PostgreSQL `17.6`, as versões e dependências existentes, a rede padrão por projeto e as conexões internas atuais.
- Não alterar os outros projetos, a configuração global do Tailscale ou o `.env` pessoal para obter a nova porta padrão.
- Prefixar comandos de shell com `rtk`; não usar `down -v`, remover volumes ou publicar a senha real nos resultados dos testes.

## Review Focus

- `.env` ausente, inclusive no estágio `/web` do Docker: Vite continua carregando com destino `8082` — tarefa 2.
- `APP_PORT` vazio: Compose e Vite usam `8082`, inclusive quando o terminal vazio sobrepõe o arquivo — tarefas 1 e 2.
- Porta definida somente no `.env` da raiz: Compose e Vite iniciado em `apps/web` usam `18082` — tarefas 1 e 2.
- Terminal define `18083` e arquivo define `18082`: ambos usam `18083` — tarefas 1 e 2.
- Alteração da porta externa: banco permanece interno, namespace e volume permanecem os mesmos; senha não aparece no ambiente do cliente Vite — tarefas 1 e 2.

---

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `docker-compose.yml:24` | Publicação da porta do app; preservar banco, rede e volume. |
| `.env.example` | Documentar `APP_PORT=8082` e seu uso opcional. |
| `tests/ops/test_compose.py` (criar) | Contrato observável da CLI Compose, sem subir containers. |
| `apps/web/vite.config.ts:1` | Ler a porta compartilhada e configurar o proxy existente. |
| `apps/web/src/test/vite-config.test.ts` (criar) | Configuração efetiva do Vite com arquivos e ambiente temporários. |
| `README.md:35` | Inicialização, configuração de porta, dev frontend e comando Tailscale. |
| `docs/05-arquitetura-e-contratos.md:15` | Diagrama, tabela de serviços e acesso Tailscale. |
| `docs/06-ux-e-fluxos.md:71` | Endereço padrão no fluxo de primeiro uso. |

## Task 1: Porta configurável no Compose com preservação do banco

**Files:** criar `tests/ops/test_compose.py`; modificar `docker-compose.yml`, `.env.example`, `README.md`, `docs/05-arquitetura-e-contratos.md` e `docs/06-ux-e-fluxos.md`.

**Interfaces:**
- Consumes: Compose e seus serviços `app`, `db`, `backup`, `test`, volume `pgdata` e rede padrão atuais.
- Produces: `APP_PORT` opcional na raiz/terminal; publicação somente em `127.0.0.1`, destino interno `8000`, padrão `8082`.
- Harness de teste: `render_compose(env_file_values: dict[str, str], shell_overrides: dict[str, str] | None = None) -> dict`, privado do teste. Executar a CLI real com `--project-directory` na raiz, `--env-file` temporário, `-f` absoluto e `--profile test config --format json`. Usar senha fictícia; remover do ambiente herdado `APP_PORT`, `POSTGRES_PASSWORD` e variáveis `COMPOSE_*` antes de aplicar os overrides. Não imprimir o JSON completo.

- [ ] **Step 1: Escrever `test_default_app_port_and_database_isolation`** no harness `unittest`. A configuração temporária contém apenas a senha fictícia. Asserções do contrato:

```python
self.assertEqual(config["services"]["app"]["ports"][0]["host_ip"], "127.0.0.1")
self.assertEqual(config["services"]["app"]["ports"][0]["published"], "8082")
self.assertEqual(config["services"]["app"]["ports"][0]["target"], 8000)
self.assertFalse(config["services"]["db"].get("ports"))
self.assertEqual(config["name"], "cgu2026")
self.assertEqual(config["volumes"]["pgdata"]["name"], "cgu2026_pgdata")
self.assertEqual(config["networks"]["default"]["name"], "cgu2026_default")
```

Também verificar que app e test continuam conectando a `@db:5432/cgu` e `@db:5432/cgu_test`, backup a `PGHOST=db`, e que o serviço `db` monta a origem `pgdata` em `/var/lib/postgresql/data`.

- [ ] **Step 2: Executar RED:** `rtk proxy python3 -m unittest discover -s tests/ops -p test_compose.py -v`. Esperado: falha por porta publicada `8080` em vez de `8082`; falhas de ferramenta/ambiente não contam como RED.
- [ ] **Step 3: Implementar o mínimo:** substituir a porta fixa publicada por `127.0.0.1:8082:8000`, preservando o restante do Compose.
- [ ] **Step 4: Executar o mesmo comando:** esperado PASS.
- [ ] **Step 5: Escrever `test_app_port_from_root_env`**, usando o arquivo temporário com `APP_PORT=18082`; esperar `published == "18082"`, mantendo `host_ip == "127.0.0.1"` e destino `8000`.
- [ ] **Step 6: Executar RED:** mesmo comando; esperado falhar porque a porta ainda é `8082`.
- [ ] **Step 7: Implementar `127.0.0.1:${APP_PORT:-8082}:8000`** em `docker-compose.yml`.
- [ ] **Step 8: Executar GREEN:** mesmo comando; esperado PASS.
- [ ] **Step 9: Acrescentar regressões do contrato**, uma por vez, executando após cada uma: arquivo com porta vazia → `8082`; arquivo `18082` + terminal `18083` → `18083`; arquivo `18082` + terminal vazio → `8082`. Esperado PASS pela interpolação nativa, sem adicionar lógica própria.
- [ ] **Step 10: Atualizar configuração de exemplo e documentação desta entrega:** adicionar `APP_PORT=8082` em `.env.example`; trocar as referências operacionais atuais a `8080` por `8082`; explicar a porta personalizada no `.env`, o banco apenas interno e o volume preservado. Comandos Tailscale devem usar a mesma porta escolhida; não executar ou reconfigurar o Tailscale. Não reescrever planos históricos.
- [ ] **Step 11: Verificar entrega:** repetir os testes da CLI e executar `rtk git diff --check`. Esperado: todos os testes PASS e nenhum erro de whitespace.
- [ ] **Step 12: Commit:** adicionar somente os seis arquivos desta tarefa e executar `rtk git commit -m "fix: configure local app port without changing postgres storage"`.

## Task 2: Proxy do Vite acompanha a porta do Compose

**Files:** modificar `apps/web/vite.config.ts` e `README.md`; criar `apps/web/src/test/vite-config.test.ts`.

**Interfaces:**
- Consumes: `APP_PORT` da tarefa 1, `.env` da raiz e ambiente do processo.
- Produces: configuração Vite com `server.proxy['/api']` apontando a `http://127.0.0.1:<porta efetiva>`; manter plugins, aliases e configuração de testes existentes.
- Harness de teste: `resolveFixture(envFile: string | undefined, shellPort: string | undefined): Promise<ResolvedConfig>`, privado do teste, usa `resolveConfig` da API pública do Vite. Criar uma árvore temporária com `apps/web/vite.config.ts` copiado do arquivo real e symlink de `apps/web/node_modules` para as dependências instaladas; escrever apenas o `.env` fictício da raiz temporária. Usar `root` e `configFile` absolutos, `mode: 'test'` e comando `'serve'`. Salvar/restaurar `process.env.APP_PORT` e limpar a árvore em `afterEach`; não tocar no `.env` pessoal nem simular módulos internos. Arquivo de teste usa `// @vitest-environment node`.

- [ ] **Step 1: Escrever `defaults_to_8082_without_root_env`**: chamar `resolveFixture(undefined, undefined)` e testar:

```typescript
expect(config.server.proxy?.['/api']).toBe('http://127.0.0.1:8082')
```

- [ ] **Step 2: Executar RED:** em `apps/web`, `rtk npm test -- src/test/vite-config.test.ts`. Esperado falhar por destino antigo `8080`.
- [ ] **Step 3: Implementar o mínimo:** trocar o destino fixo atual do proxy para `http://127.0.0.1:8082`.
- [ ] **Step 4: Executar GREEN:** repetir o teste; esperado PASS.
- [ ] **Step 5: Escrever `uses_port_from_repository_root_env`**, com `.env` temporário `APP_PORT=18082`; esperar proxy `http://127.0.0.1:18082`.
- [ ] **Step 6: Executar RED:** mesmo comando; esperado falhar pelo destino ainda fixo em `8082`.
- [ ] **Step 7: Ler somente a configuração necessária:** resolver o caminho `../../.env` a partir de `import.meta.dirname` do config. Se existir, usar `readFileSync` de `node:fs` e `parseEnv` de `node:util` para obter `APP_PORT`, com fallback `8082` para vazio/ausente. Não adicionar biblioteca nem popular `process.env`, `define` ou `envPrefix` com o conteúdo desse arquivo. Não usar `.env.local` ou variantes por modo para esta porta compartilhada.
- [ ] **Step 8: Executar GREEN:** repetir o teste; esperado PASS.
- [ ] **Step 9: Escrever `shell_port_overrides_repository_env`**, com arquivo `APP_PORT=18082` e terminal `APP_PORT=18083`; esperar proxy `http://127.0.0.1:18083`.
- [ ] **Step 10: Executar RED:** mesmo comando; esperado falhar porque somente o arquivo é considerado.
- [ ] **Step 11: Aplicar a precedência:** escolher `process.env.APP_PORT ?? arquivo.APP_PORT` e depois fallback `8082` para string vazia/ausente. Construir o destino do proxy a partir dessa porta efetiva.
- [ ] **Step 12: Executar GREEN:** repetir o teste; esperado PASS.
- [ ] **Step 13: Acrescentar regressões do contrato**, uma por vez: arquivo vazio → `8082`; terminal vazio sobre arquivo `18082` → `8082`; terminal `18083` sem arquivo → `18083`; arquivo com senha fictícia → `config.env.POSTGRES_PASSWORD` é `undefined`. Executar após cada caso; esperado PASS sem lógica adicional.
- [ ] **Step 14: Atualizar README:** documentar `npm run dev` em `apps/web`, usando a mesma `APP_PORT` da raiz; depois de mudar a porta, reiniciar o Vite e recriar o app com Compose. O build de produção não depende da existência de `.env`.
- [ ] **Step 15: Verificar frontend e integração das configurações:** em `apps/web`, executar `rtk npm test`, `rtk npm run build` e `rtk npm run lint`; na raiz, repetir os testes da CLI. Esperado: testes, build e lint sem falhas.
- [ ] **Step 16: Verificar em execução:** registrar os containers ativos e a identidade do volume existente; executar `rtk docker compose up -d --build`; verificar `rtk docker compose ps` e `rtk proxy curl --fail http://127.0.0.1:8082/api/v1/health` (usar a porta efetiva caso exista override). Esperado: HTTP 200, db saudável sem porta no host, app somente em loopback e volume montado `cgu2026_pgdata`; outros projetos continuam ativos. Não executar testes de API contra o banco principal. Se houver bloqueio ambiental, registrar o bloqueio sem afirmar sucesso.
- [ ] **Step 17: Atualizar grafo e conferir alterações:** `rtk proxy graphify update .`, `rtk git diff --check` e revisar o diff. Esperado: grafo atualizado e nenhuma alteração fora do escopo; não adicionar automaticamente artefatos do grafo ao commit da funcionalidade.
- [ ] **Step 18: Commit:** adicionar somente Vite config, seu teste e README; executar `rtk git commit -m "fix: align vite api proxy with compose app port"`.

## Revisão do plano

Cobertura conferida: os dois contratos públicos cobrem o padrão, override, vazio, precedência e persistência; documentação acompanha cada entrega. A verificação operacional confirma o caminho HTTP real e a coexistência. Não há atualização de dependências, abertura da porta do PostgreSQL ou exclusão/migração de volume planejada. O início normal do app mantém seu comportamento existente de migrações e seed idempotente.

## Referências técnicas

- [Docker: interpolação, defaults e precedência de variáveis](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/).
- [Vite: API JavaScript pública](https://vite.dev/guide/api-javascript.html); assinatura de `resolveConfig` também conferida em `apps/web/node_modules/vite/dist/node/index.d.ts`.
- [Node: `util.parseEnv`](https://nodejs.org/api/util.html#utilparseenvcontent).

## Handoff

Antes de escrever testes ou código, obter a revisão deste plano, a confirmação das fronteiras Compose CLI e Vite config e a escolha de execução. Recomendada: execução nativa nesta sessão, com `superpowers:executing-plans` e ciclos de `mattpocock-skills:tdd`; são duas tarefas pequenas e sequenciais. Nessa modalidade, um revisor independente verifica o conjunto ao final. Se escolhida execução por subagentes, usar `superpowers:subagent-driven-development`, com implementação e revisão independentes por tarefa e revisão do conjunto ao final.
