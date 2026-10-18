# Compatibilidade do arranque com a revisão existente — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans para execução nativa, com mattpocock-skills:tdd. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer a imagem reconhecer a migração já aplicada ao banco e comprovar o arranque por teste isolado, preservando os dados reais.

**Architecture:** Recuperar exatamente a migração histórica `5c9e1f3a7b21` de `86da02ea6498c440b6f723733764233b03659415`, da branch `feat/blocos-e-orientacoes`, sem integrar suas outras funcionalidades. Testar a imagem pelo processo normal de arranque e por HTTP usando PostgreSQL descartável que reproduz a revisão observada.

**Tech Stack:** Docker/Compose, PostgreSQL 17.6, imagem runtime existente, Python unittest/subprocess/urllib da biblioteca padrão. Sem novas dependências. No banco real, a revisão e a coluna já existem: o arranque esperado não aplica DDL. Em bancos novos ou na revisão `2a16732b4a43`, a migração recuperada passa a adicionar `theme_id` normalmente; esse é o efeito de reincorporar o histórico nesta branch.

**Spec:** [Desenho original](../specs/2026-10-17-containers-coexistencia-local-design.md) e [retomada](2026-10-17-coexistencia-local-retomada.md). Evidência sanitizada: `.superpowers/sdd/2026-10-17-coexistencia-local-retomada/diagnostico.md`.

**Status:** Microplano e fronteira startup/HTTP aprovados pelo usuário em 17/10/2026. Task 1 executada com RED→GREEN, commit `bfd429b`; aceitação HTTP/estabilidade real comprovada; revisão independente final concluída sem achados críticos ou importantes. As fronteiras Compose CLI e Vite já confirmadas continuam válidas.

## Global Constraints

- Preservar projeto `cgu2026`, volume `cgu2026_pgdata`, bancos `cgu`/`cgu_test`, backups, dependências e demais projetos.
- App real somente em `127.0.0.1:${APP_PORT:-8082}:8000`; banco real sem publicação no host.
- Não gerar revisão nova, reescrever migração histórica, executar stamp, UPDATE de alembic_version, restauração ou teste destrutivo nos bancos existentes.
- Todo preparo artificial de esquema/revisão ocorre apenas no PostgreSQL descartável do teste, com senha fictícia e armazenamento tmpfs exclusivo.
- Somente reincorporar o arquivo histórico; nenhuma alteração em modelos, seed, UX ou comportamento dos blocos.
- Prefixar comandos de shell com `rtk`. Preservar evidências e não expor credenciais pessoais.

## Review Focus

1. Banco numa revisão de outra branch: teste deve falhar com a revisão ausente e passar com o arquivo histórico restaurado.
2. Fixture não pode acessar bancos/volumes existentes: gerar projeto/rede exclusivos, usar tmpfs e somente senha fictícia.
3. Processo em execução sem HTTP não basta: verificar HTTP 200 e `{"status":"ok"}`, com timeout e logs em falha.
4. Arquivo histórico deve manter identidade e parentesco: comparar com o blob original, sem criação de revisão substituta.
5. Aceitação real exige confirmar revisão e mount antes do app; nenhum reparo de dados/esquema está autorizado por este documento.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `tests/ops/test_startup.py` | Teste de regressão pelo arranque real da imagem; fixtures descartáveis. |
| `apps/api/migrations/versions/20261010_5c9e1f3a7b21_occurrence_theme.py` | Migração histórica recuperada sem modificações. |
| `README.md` | Comando do teste de arranque e pré-requisito de imagem construída. |

## Fronteira proposta para confirmação

**Processo normal da imagem runtime + API HTTP**, sem mocks ou importação de funções internas. O teste usa a imagem local `cgu2026-app` (override `CGU_STARTUP_IMAGE`), PostgreSQL 17.6 descartável e configuração Compose temporária. Observa disponibilidade HTTP e logs/estado do processo para diagnosticar falhas. A fixture SQL configura a condição inicial; as assertions de sucesso usam HTTP.

## Task 1: Restaurar a migração com regressão RED → GREEN

**Interfaces:** Consumes: imagem runtime, commit histórico e estado confirmado `5c9e1f3a7b21`. Produces: teste `StartupTests.test_starts_with_already_applied_occurrence_theme_revision`, arquivo histórico restaurado e HTTP disponível na fixture.

- [x] **Step 1: Confirmar esta fronteira e revisar este microplano com o usuário.** Somente depois escrever o teste. Não confundir os testes existentes verdes com um novo ciclo RED.
- [x] **Step 2: Criar o único teste de regressão em `tests/ops/test_startup.py`.** Usar `unittest`, sem carregar fixtures de `apps/api/tests/integration`. Gerar nome de projeto `cgu-startup-<UUID>` e arquivo Compose temporário que não depende do `.env` pessoal: db `postgres:17.6`, database `cgu_startup_test`, usuário `cgu`, senha `fixture-password`, tmpfs `/var/lib/postgresql/data`, healthcheck; app usa a imagem selecionada, DATABASE_URL fictícia, ALLOWED_HOSTS `127.0.0.1,localhost`, porta aleatória exclusivamente em loopback, restart desativado. Sem mounts do projeto, backups, volumes nomeados ou rede externa.
- [x] **Step 3: Preparar somente a fixture descartável.** Subir db com timeout; executar via imagem `alembic upgrade 2a16732b4a43 && python -m app.seed`. Via psql no db descartável, adicionar `occurrences.theme_id varchar(16)` nullable e registrar `5c9e1f3a7b21` em alembic_version. Essas operações reproduzem a condição histórica sem exigir o arquivo ausente. Iniciar app com CMD original; descobrir porta por `compose port`; aguardar até 30 s usando relógio monotônico e encerrar cedo se o processo sair. Assert HTTP status `200` e JSON literal `{"status": "ok"}`; confirmar HTTP 200 em `/api/v1/subjects` e `total == 13`, exercitando o catálogo persistido pelo seed. Capturar logs em falha. Registrar limpeza com addCleanup assim que o projeto existir; remover somente containers/rede desse projeto, sem tocar nos projetos existentes. Erros de ferramenta/setup não contam como RED.
- [x] **Step 4: Observar RED.** `rtk proxy python3 -m unittest discover -s tests/ops -p test_startup.py -v`. Esperado: assertion de disponibilidade falha; processo sai com log `Can't locate revision identified by '5c9e1f3a7b21'`. Se falhar por outro motivo, corrigir apenas a fixture e repetir antes do patch.
- [x] **Step 5: Recuperar a implementação mínima.** Escrever `apps/api/migrations/versions/20261010_5c9e1f3a7b21_occurrence_theme.py` com o conteúdo exato de `git show 86da02ea6498c440b6f723733764233b03659415:apps/api/migrations/versions/20261010_5c9e1f3a7b21_occurrence_theme.py`. `revision=5c9e1f3a7b21`, `down_revision=2a16732b4a43`; upgrade adiciona somente theme_id nullable, downgrade remove a coluna. Não executar downgrade nem stamp.
- [x] **Step 6: Construir e observar GREEN.** `rtk docker compose build app`, depois o comando do Step 4. Esperado: build PASS, teste PASS e fixture removida. Não iniciar o app real ainda. Comparar conteúdo do arquivo recuperado com o blob de origem; esperado: igualdade byte a byte.
- [x] **Step 7: Verificar regressões e documentar.** Executar `rtk proxy python3 -m unittest discover -s tests/ops -v`, `rtk npm test`, `rtk npm run build`, `rtk npm run lint` em apps/web para comandos npm, e `rtk git diff --check`. API: suíte completa somente em projeto PostgreSQL separado com database terminado em `_test`, nunca o cgu_test existente. Acrescentar ao README o comando de startup, a necessidade de Docker/imagem construída e o isolamento. Alterar o comando atual de configuração sem containers para `python3 -m unittest discover -s tests/ops -p test_compose.py -v`: após acrescentar test_startup.py, o discovery genérico passa a iniciar os containers descartáveis. Esperado: nenhum teste falha; avisos existentes registrados separadamente.
- [x] **Step 8: Commit.** Adicionar somente migração, `tests/ops/test_startup.py` e README; mensagem `fix: include applied occurrence theme migration in runtime history`.

## Task 2: Aceitação no ambiente real

**Interfaces:** Consumes: Task 1 GREEN. Produces: evidência de estabilidade, isolamento e revisão preservada para Task 4 da retomada.

- [x] **Step 1: Conferir por leitura antes de iniciar.** Mount `cgu2026_pgdata`, banco `cgu`, alembic_version `5c9e1f3a7b21`, coluna theme_id nullable e contagens de sessões/ocorrências/missões. Se diferir da evidência registrada ou exigir alteração de dados/esquema, parar e pedir decisão específica.
- [x] **Step 2: Iniciar somente app.** `rtk docker compose up -d --no-deps app`. O upgrade deve reconhecer a revisão já aplicada sem DDL pendente. Backup e demais projetos não são reiniciados.
- [x] **Step 3: Validar HTTP e estabilidade.** Health na porta efetiva, JSON `{"status":"ok"}`, app running sem crescimento do restart count em duas observações separadas por 30 s. Inspecionar logs sanitizados, db sem porta host e volume preservado; comparar IDs dos outros projetos. Repetir consultas de leitura para revisão/contagens, sem gravar sessões de teste reais.
- [x] **Step 4: Revisão independente final.** Revisar o conjunto e os cinco focos; registrar achados. Atualizar ledger da retomada e grafo ignorado conforme plano original. Não fazer push/merge.

## Autorrevisão

A causa e o patch são concretos e rastreáveis ao Git. A recuperação acrescenta histórico à imagem sem alterar a revisão real. O teste cobre a incompatibilidade que create_all não observa; o schema artificial fica exclusivamente na fixture. A validação real permanece obrigatória. A fronteira foi aprovada; o teste reproduziu a revisão ausente antes do patch e passou após recuperar o arquivo histórico. Suítes: 6 operacionais, 81 API e 26 frontend verdes. A aceitação da Task 2 foi comprovada e a revisão independente não identificou bloqueadores.

## Resultado registrado em 17/10/2026

- Commit de correção: `bfd429b`. Migração histórica idêntica ao blob de `86da02e`.
- RED: processo saiu antes de responder HTTP, com revisão `5c9e1f3a7b21` ausente. GREEN: seis testes operacionais, 81 API em banco isolado e 26 frontend aprovados; builds e lint com saída zero.
- App real em `http://127.0.0.1:8082`: saúde e catálogo HTTP 200; mesmo container e zero reinícios em duas observações separadas por 30 s.
- Revisão do banco `5c9e1f3a7b21`, 10 sessões, 18 ocorrências e 5 missões mantidas. Volume real `cgu2026_pgdata`, banco sem porta publicada e IDs de banco/backup/demais projetos preservados.
- Revisão independente final: nenhum Critical/Important; Declined to judge vazio. Melhoria Minor adiada: capturar logs também quando falham assertions/JSON/consulta de catálogo no teste de arranque, antes de remover a fixture. A limitação afeta diagnóstico, não o GREEN observado.
- Avisos preexistentes: oito de lint, bundle frontend ~810 kB, depreciação Starlette/httpx na suíte API. Grafo de código atualizado (942 nós/1854 arestas), com avisos preexistentes de extração; artefatos ignorados.
- Branch mantida sem push ou merge. Evidências locais preservadas no workspace ignorado da execução, conforme o requisito de preservação de evidências.
