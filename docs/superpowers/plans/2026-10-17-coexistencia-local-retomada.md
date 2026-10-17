# Retomada da coexistência local — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Execution chosen:** `superpowers:executing-plans` (nativa), com `mattpocock-skills:tdd` para qualquer correção posterior: um teste falhando e uma implementação mínima por ciclo.

**Goal:** Concluir a entrega de coexistência local, diagnosticando a reinicialização do app, corrigindo sua causa mínima quando estiver no escopo e comprovando o funcionamento antes do fechamento.

**Architecture:** Reaproveitar a configuração Compose/Vite e os testes já implementados. Obter primeiro a evidência da falha na sequência `alembic upgrade head && python -m app.seed && exec uvicorn ...`; a causa determina a correção e sua regressão. Separar acesso ao ambiente, correção em ambiente isolado e aceitação no projeto real.

**Tech Stack:** Docker Compose existente, PostgreSQL 17.6, Node 24, Python da imagem existente, unittest, pytest, Vite/Vitest e TypeScript existentes.

**Spec:** [Desenho original](../specs/2026-10-17-containers-coexistencia-local-design.md) e [plano anterior](2026-10-17-containers-coexistencia-local.md). Extensão aprovada na conversa: incluir correção mínima da inicialização da API/imagem, se necessária; novas alterações de esquema ou recuperação de dados exigem decisão específica antes da execução. Execução nativa recomendada e aprovada; uma revisão independente do conjunto ao final.

## Global Constraints

- Preservar o projeto Compose `cgu2026`, o volume existente `cgu2026_pgdata`, seus dados, o banco `cgu`, o banco de testes `cgu_test` e os backups.
- A aplicação publica `127.0.0.1:${APP_PORT:-8082}:8000`.
- `APP_PORT` é opcional: ausente ou vazio significa `8082`; um valor configurado é uma porta TCP decimal válida. A variável do terminal tem precedência sobre o `.env` da raiz.
- Cada projeto tem seu próprio PostgreSQL. Este banco é acessível somente pelos containers, em `db:5432`, sem publicação de porta no host.
- Manter PostgreSQL `17.6`, as versões e dependências existentes, a rede padrão por projeto e as conexões internas atuais.
- Não alterar os outros projetos, a configuração global do Tailscale ou o `.env` pessoal para obter a nova porta padrão.
- Prefixar comandos de shell com `rtk`; não usar `down -v`, remover volumes ou publicar a senha real nos resultados dos testes.
- Respeitar o sandbox. Se Git/Docker continuarem bloqueados, registrar a operação e o erro; não contornar restrições nem repetir tentativas sem mudança de acesso.
- Não executar testes de integração, `drop_all`, `TRUNCATE`, restauração ou experimentos no banco principal. A fixture atual de integração é destrutiva e só admite database `*_test`.
- Não recriar serviços para tentar adivinhar a falha: iniciar o app executa migrações e seed, que escrevem no banco. Reiniciar `backup` também aplica retenção de arquivos.
- Avisos existentes de lint, tamanho do bundle e extração do grafo ficam fora desta entrega. Não atualizar dependências como tentativa de correção.

## Review Focus

- `255` não identifica a causa: diagnóstico deve distinguir falha do processo, migração, seed e servidor, sem tratar erro de acesso como evidência do defeito — tarefa 2.
- App deve permanecer ativo e responder HTTP; apenas build aprovado ou `compose up` com saída zero não basta — tarefa 4.
- Configuração de volume não prova o mount real; conferir o volume efetivamente montado antes de iniciar o app — tarefas 2 e 4.
- HTTP 200 em `/health` não comprova integridade do banco, pois a rota não consulta persistência; conferir identidade e migração separadamente, somente por leitura — tarefa 4.
- `.env` ausente/vazio, precedência do terminal e isolamento de segredos continuam cobertos pelos testes existentes; a correção de startup não pode regressar esses contratos — tarefas 1 e 4.

---

## Estado reavaliado em 17/10/2026

- Tarefa 1 concluída: cinco testes Compose e 26 testes frontend verdes; build/lint com saída zero e avisos preexistentes. Commits `eb88d00` e `9997ea1` preservam a implementação original.
- Tarefa 2 concluída: acesso Docker normal disponível. Mount real `cgu2026_pgdata` confirmado; app falha em Alembic porque banco registra `5c9e1f3a7b21`, ausente da imagem. Essa migração existe em `86da02e`, na branch `feat/blocos-e-orientacoes`, que não é ancestral da branch atual. Não é uma falha de porta nem evidência de corrupção.
- Tarefa 3 concluída: [microplano concreto](2026-10-17-coexistencia-local-correcao-startup.md) e fronteira startup/HTTP aprovados pelo usuário. Regressão RED observada pela revisão ausente; GREEN após recuperar byte a byte a migração de `86da02e`. Commit `bfd429b` inclui migração histórica, teste e README.
- Tarefa 4: aceitação operacional comprovada após recriar somente o app. Health e catálogo HTTP 200 em duas observações separadas por 30 s, restart count 0, binding somente em `127.0.0.1:8082`. Revisão `5c9e1f3a7b21`, contagens (10 sessões, 18 ocorrências, 5 missões), volume e demais containers preservados. Revisão independente final concluída sem achados críticos ou importantes; nenhum stamp, reparo de dados, DDL corretivo, reinício do backup, push ou merge.
- Crítica: testes API atuais recriam esquema com metadata e não percorrem migrações; não detectam esta divergência entre branch e revisão persistida. A nova regressão observa arranque real/HTTP num banco descartável. Verificação final: 6 testes operacionais, 81 API e 26 frontend verdes, builds/lint com saída zero e avisos preexistentes.

## Estado de entrada e mapa de arquivos

Estado observado em `aad92f0`, branch `feat/coexistencia-local`: oito arquivos de implementação/documentação modificados ou novos, sem commits. Os cinco testes Compose, 26 testes frontend e builds local/Docker passaram na execução anterior; a revisão independente não encontrou problemas. Esses resultados são históricos e serão revalidados. O app foi observado em `Restarting (255)`, health indisponível. Mount real e erro bruto de startup não foram acessíveis.

| Arquivo | Responsabilidade nesta retomada |
|---|---|
| `docker-compose.yml`, `.env.example`, `tests/ops/test_compose.py` | Preservar e registrar a entrega Compose já testada. |
| `apps/web/vite.config.ts`, `apps/web/src/test/vite-config.test.ts` | Preservar e registrar a entrega Vite já testada. |
| `README.md`, `docs/05-arquitetura-e-contratos.md`, `docs/06-ux-e-fluxos.md` | Preservar documentação pronta; atualizar README somente se o diagnóstico demonstrar nova instrução necessária. |
| `Dockerfile:30`, `apps/api/migrations/env.py`, `apps/api/app/seed.py`, `apps/api/app/main.py` | Inspecionar a sequência de inicialização; não são alvos presumidos de alteração. |
| `.superpowers/sdd/2026-10-17-containers-coexistencia-local/progress.md` | Consultar o histórico anterior, preservando seu registro. |
| `.superpowers/sdd/2026-10-17-coexistencia-local-retomada/progress.md` | Ledger próprio desta retomada, criado na execução. |
| `.superpowers/sdd/2026-10-17-coexistencia-local-retomada/diagnostico.md` | Evidência sanitizada da tarefa 2, criada na execução. |
| `docs/superpowers/plans/2026-10-17-coexistencia-local-correcao-startup.md` | Microplano TDD, criado na tarefa 3 apenas se houver defeito de código/imagem confirmado. |

Não há `CONTEXT.md` ou ADR encontrado no levantamento atual. Antes de executar, conferir instruções adicionais que tenham sido acrescentadas.

## Task 1: Preservar e registrar a implementação existente

**Files:** os oito arquivos da entrega original no mapa acima; ledger próprio.

**Interfaces:** Consumes: working tree revisada contra `aad92f0`. Produces: dois commits verificáveis, sem novas alterações de comportamento; estado de acesso ao Git registrado.

- [x] **Step 1: Conferir contexto e mudanças.** Executar `rtk git status --short --branch`, `rtk git log -5 --oneline` e revisar diff e arquivos novos. Esperado: identificar precisamente alterações desta entrega; preservar trabalho novo do usuário. Não repetir testes RED ou reimplementar o que já existe.
- [x] **Step 2: Revalidar Compose.** Na raiz: `rtk proxy python3 -m unittest discover -s tests/ops -p test_compose.py -v`. Esperado: cinco testes PASS cobrindo porta padrão, arquivo, valores vazios, precedência e isolamento/persistência configurados.
- [x] **Step 3: Revalidar frontend.** Em `apps/web`: `rtk npm test`, `rtk npm run build`, `rtk npm run lint`. Esperado: pelo menos os 26 testes conhecidos PASS, build e lint com saída zero. Registrar separadamente avisos preexistentes; qualquer falha nova exige investigação.
- [x] **Step 4: Conferir whitespace.** Na raiz: `rtk git diff --check`. Esperado: saída zero e nenhum erro.
- [x] **Step 5: Registrar Compose quando o ambiente permitir Git.** Adicionar somente `docker-compose.yml`, `.env.example`, `tests/ops/test_compose.py`, `docs/05-arquitetura-e-contratos.md` e `docs/06-ux-e-fluxos.md`; commit `fix: configure local app port without changing postgres storage`. Esperado: commit com esses cinco arquivos.
- [x] **Step 6: Registrar Vite e README.** Adicionar somente `apps/web/vite.config.ts`, `apps/web/src/test/vite-config.test.ts` e `README.md`; commit `fix: align vite api proxy with compose app port`. Esperado: commit com esses três arquivos. O README já reúne ambas as entregas; mantê-lo inteiro neste commit evita reescrever ou dividir artificialmente a working tree.

Se `.git/index.lock` continuar bloqueado, marcar commits como pendentes; tarefas de leitura/diagnóstico podem prosseguir se o acesso Docker estiver disponível. Testes verdes não significam commit concluído. Registrar este plano em commit próprio de documentação quando Git estiver disponível, sem incluí-lo nos dois commits acima.

## Task 2: Identificar a causa com evidência operacional

**Files:** criar somente `diagnostico.md` no workspace próprio; não alterar código nesta tarefa.

**Interfaces:** Consumes: serviços existentes e acesso normal aos diagnósticos Docker. Produces: relatório com estado observado, identidade do volume, erro sanitizado, etapa que falhou, reprodução possível e classificação da causa.

- [x] **Step 1: Verificar se o contexto de acesso mudou.** Se o mesmo sandbox ainda negar logs/inspect, registrar o bloqueio e a necessidade de executar diagnósticos em ambiente com acesso normal ao Docker. Não repetir o build ou a recriação; não afirmar causa técnica sem logs.
- [x] **Step 2: Registrar a linha de base dos containers.** Quando houver acesso, executar `rtk docker ps --format '{{.ID}} {{.Names}} {{.Status}} {{.Ports}}'` e `rtk docker compose ps -a`. Esperado: registrar IDs/estado dos demais projetos e estado atual de `app`, `db`, `backup`, sem mutações.
- [x] **Step 3: Inspecionar apenas campos necessários.** Para `cgu2026-db-1`, observar mounts de tipo volume, destino e porta publicada; para `cgu2026-app-1`, estado, exit code, erro do runtime, contador de reinícios e bindings. Esperado: mount `cgu2026_pgdata` em `/var/lib/postgresql/data`, db sem binding no host; evidência do estado do app. Usar formatos restritos de `docker inspect`; não imprimir `Config.Env` nem inspect completo.
- [x] **Step 4: Obter o erro real.** Capturar `rtk proxy docker compose logs --no-color --tail 100 app` em arquivo local ignorado e sanitizar antes de apresentar trechos. Esperado: erro suficiente para localizar a etapa; logs vazios exigem analisar `State.Error`, não concluir que a API está correta. Não publicar URLs com credenciais.
- [x] **Step 5: Classificar e documentar.** Preencher `diagnostico.md` com evidência, etapa, causa demonstrada ou lacuna restante e próximo caminho: acesso ainda bloqueado; defeito de código/imagem; problema de ambiente; ou necessidade de reparo de esquema/dados. Esperado: cada conclusão apoiada por saída real, sem trocar senha, mexer em permissões globais ou reparar banco.

**Gate:** se os logs não estiverem acessíveis, o diagnóstico permanece bloqueado. Se houver divergência do volume ou necessidade de novas migrações, alteração de esquema ou recuperação de dados, apresentar evidências e obter decisão específica antes de qualquer reparo. Reexecutar migrações já existentes faz parte do arranque normal; criar migração corretiva não está previamente autorizado.

## Task 3: Definir e executar a correção mínima por TDD

**Files:** criar o microplano de correção indicado no mapa somente após a tarefa 2. Arquivos de produção e regressão serão fixados nesse documento a partir da causa demonstrada; não antecipar alterações no Dockerfile ou na API.

**Interfaces:** Consumes: `diagnostico.md` com causa reproduzível. Produces: correção mínima com regressão RED→GREEN e commit próprio, ou conclusão documentada de que não há mudança de código necessária.

- [x] **Step 1: Selecionar o caminho pela evidência.** Sem defeito reproduzível, não escrever teste nem patch. Se o problema for exclusivamente ambiental, documentar a ação necessária no relatório e, quando aplicável, no README; não inventar um teste de código para uma falha de acesso.
- [x] **Step 2: Para defeito de código/imagem, escrever o microplano com `superpowers:writing-plans`.** Deve conter causa, arquivos exatos, fixture mínima reproduzindo o estado observado, nome/assertions do teste, comando RED, alteração mínima, comando GREEN, suíte pertinente e mensagem de commit. Esperado: documento executável sem placeholders. Esta etapa é necessária porque `255` não determina hoje qual código corrigir.
- [x] **Step 3: Confirmar a fronteira nova antes do primeiro teste.** Usar `mattpocock-skills:tdd`; as fronteiras Compose CLI e Vite config já estão acordadas. Recomendada para falha de startup: processo real de arranque da imagem, com PostgreSQL/volume isolados e senha fictícia, observando exit code e disponibilidade HTTP. Se a causa exigir uma fronteira diferente, descrevê-la no microplano e confirmar com o usuário.
- [x] **Step 4: Executar o microplano aprovado.** Um teste por vez: observar a falha pelo defeito, implementar o mínimo e observar PASS. Erro de ferramenta não conta como RED. Se precisar de dados, usar banco e armazenamento exclusivos de teste; não apontar fixtures destrutivas ao `cgu` ou ao `cgu_test` existente sem isolamento específico.
- [x] **Step 5: Verificar e registrar.** Rodar a suíte do componente afetado, além das verificações de configuração da tarefa 1; revisar diff e `rtk git diff --check`. Esperado: regressão e suíte PASS; commit próprio da correção quando Git permitir. Sem mudança de código necessária, registrar esse resultado com a evidência da ação ambiental aplicada.

Esta é uma entrega em duas etapas de especificação: o presente plano torna o diagnóstico executável; o microplano torna a correção executável quando a causa for conhecida. Não substituir essa dependência por uma correção especulativa.

## Task 4: Comprovar execução e encerrar a branch

**Files:** ledger próprio; `README.md` somente se houver instrução operacional nova comprovada.

**Interfaces:** Consumes: correção/ação ambiental validada, acesso Docker e volume real identificado. Produces: evidência de saúde, isolamento e coexistência; revisão final e commits pendentes concluídos ou explicitamente bloqueados.

- [x] **Step 1: Conferir o banco por leitura.** Confirmar database `cgu`, identidade/mount já registrado e revisão Alembic atual compatível com o head existente. Usar consultas de leitura com credenciais internas do container, sem imprimir segredos. Esperado: identidade correta e esquema conhecido; interromper diante de drift, sem corrigir automaticamente. Não usar health como prova de integridade de dados.
- [x] **Step 2: Construir a imagem se houve correção de código/imagem.** `rtk docker compose build app`. Esperado: build PASS, incluindo frontend em `/web` sem `.env` da raiz.
- [x] **Step 3: Iniciar somente o app necessário.** Com db saudável e volume conferido: `rtk docker compose up -d --no-deps app`. Esperado: app ativo na porta efetiva de `APP_PORT`. Evitar reiniciar `backup` e aplicar retenção novamente; não alterar outros projetos.
- [x] **Step 4: Verificar HTTP e estabilidade.** `rtk proxy curl --fail --silent --show-error http://127.0.0.1:8082/api/v1/health`, substituindo a porta se houver override efetivo. Esperado: HTTP 200 e `{"status":"ok"}`. Conferir estado e contador de reinícios em duas observações separadas por 30 segundos; esperado: app permanece ativo, contador não cresce. Registrar erro/timeout como falha, não repetir restart como correção.
- [x] **Step 5: Conferir isolamento e coexistência reais.** Comparar mounts, bindings e containers com a tarefa 2. Esperado: app somente `127.0.0.1:<porta>:8000`, db sem publicação, mount `cgu2026_pgdata` preservado; IDs dos outros projetos continuam ativos. Não executar gravações de teste no app principal.
- [x] **Step 6: Fazer revisão final.** Uma revisão independente do diff total, incluindo eventuais correções, sem repetir a implementação original. Verificar os cinco itens de Review Focus. Achados relevantes exigem reprodução e correção TDD; preservar o registro da revisão anterior.
- [x] **Step 7: Encerrar o registro.** `rtk git diff --check`, `rtk git status --short --branch` e conferência dos commits. Esperado: arquivos desta entrega commitados, testes e operação comprovados, nenhum trabalho alheio incluído. Atualizar o grafo apenas se houver nova mudança de código, mantendo seus artefatos ignorados. Não fazer push ou merge sem instrução.

## Critério de conclusão e handoff

Entrega concluída somente com implementação preservada, correção mínima comprovada quando necessária, testes pertinentes verdes, app estável/respondendo, isolamento/volume/coexistência inspecionados e commits registrados. Bloqueio de acesso ou falha HTTP impede declarar conclusão, mesmo com builds e testes verdes.

O plano deve ser revisado antes da implementação. Manter execução nativa com `superpowers:executing-plans` e `mattpocock-skills:tdd`; não começar a tarefa 3 sem o diagnóstico e o microplano concreto. A autorização de correção mínima já foi dada; só pedir nova decisão para a fronteira de teste nova, revisão do microplano ou situações fora dos limites aprovados.

## Autorrevisão do plano

Cobertura: tarefas 1 e 4 preservam os contratos originais; tarefa 2 elimina a inferência de causa a partir de `255`; tarefa 3 inclui a correção mínima aprovada, sem presumir arquivo/defeito. Os cinco focos têm verificações explícitas. Não há atualização de dependências, reparo de dados, mudança de esquema, reconfiguração Tailscale ou refatoração planejada. A lacuna factual original foi resolvida por logs/inspeção e consultas somente leitura nesta retomada; o microplano de correção foi aprovado e executado antes da aceitação real.
