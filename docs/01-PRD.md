# PRD — Assistente de estudos gamificado CGU 2026

Versão 2.0 · 09/10/2026.

## 1. Problema

O plano web atual apresenta conteúdo e rotina, mas não registra execução nem ajuda a manter constância. São necessários um lugar para ver o que fazer hoje, registrar sessões, relacionar resultados a tópicos do edital e organizar revisões e treino discursivo, e um mecanismo que torne a rotina diária visível e motivadora até a prova de 13/12/2026.

## 2. Usuário e contexto

Usuário único: Rubens, formado em Engenharia de Software (sua base mais forte), com experiência em PHP/JavaScript/MySQL, aplicações internas, APIs, suporte e contratação de TI. Essa base é vantagem de partida para P3, mas não comprova domínio de Java/Spring/JPA/Batch/Vue, do conteúdo geral da CGU (P1/P2) ou de escrita de prova.

Rotina declarada: uma hora antes do trabalho, uma intermediária e uma depois. O período intermediário só será usado quando autorizado e compatível com as atividades profissionais; é remanejável. Não fixar horários de relógio. Fins de semana opcionais.

Uso **pessoal e local**: o aplicativo roda no Mac do usuário via Docker e é acessado pelo navegador do Mac e pelo celular através da rede privada Tailscale. Não há login.

## 3. Objetivo e jornada principal

Abrir o app, **abrir o dia**, ver a missão (blocos, revisões vencidas, meta de questões), estudar com materiais externos e registrar cada sessão em menos de dois minutos, recebendo XP e mantendo a sequência. A partir desses registros, consultar metas, revisões e progresso sem confundir cobertura com domínio, XP com preparo ou cumprimento de mínimos com classificação.

O app passa a ser usado **a partir de 09/10/2026**: a primeira fatia (v1) precisa estar utilizável no mesmo dia.

## 4. Requisitos funcionais

| ID | Requisito | Aceitação resumida | Fatia |
|---|---|---|---|
| RF01 | Exibir perfil do concurso e catálogo por P1/P2/P3 | 13 disciplinas, 68 tópicos macro, referência ao edital | F1 |
| RF02 | Gerar ciclo de 15 blocos semanais | 900 min: 420 específicos, 180 básicos, 180 complementares, 120 discursivas; semana inicial parcial em 09/10 | F1 |
| RF03 | Consultar e remanejar blocos | Alterações futuras não modificam sessões já registradas | F1 |
| RF04 | Registrar sessões e concluir bloco | Tempo real, tópico, data, observação; persistido no Postgres | F1 |
| RF12 | Missão do dia | Abrir o dia, itens congelados, “não se aplica”, conclusão derivada ([10](10-gamificacao-e-rotina.md) §2) | F1 |
| RF13 | XP, nível e sequência | Derivados dos registros; HUD sempre visível ([10](10-gamificacao-e-rotina.md) §3–5) | F1 |
| RF14 | Instalação no celular | PWA com manifest e ícone; sem offline | F1 |
| RF05 | Registrar lotes de questões | Quantidades validadas, fonte externa, nota líquida e amostra | F2 |
| RF06 | Caderno de erros | Tópico, causa, explicação, referência; sem exigir enunciado | F2 |
| RF15 | Metas semanais | Planejado × realizado para minutos, blocos, questões, discursivas, missões | F2 |
| RF07 | Revisões | Sugestões 1/7/21 dias, conclusão manual, atrasadas; itens na missão | F3 |
| RF08 | Treinos discursivos | Tipo, duração, linhas, texto opcional, rubrica qualitativa | F4 |
| RF16 | Etapas, chefões e rebalanceamento | 4 etapas, chefões por conclusão, sugestão após diagnóstico | F4 |
| RF09 | Painel de progresso | Horas reais, blocos, cobertura, resultados por prova | F5 |
| RF17 | Conquistas | 16 conquistas derivadas | F5 |
| RF10 | Exportar e restaurar dados | JSON versionado; restauração validada, sem duplicação | F5 |

RF11 (identidade autenticada) foi **removido** na v2.0: o app é local e de usuário único. Reintroduzir identidade é pré-requisito para qualquer uso multiusuário ou exposição fora da rede Tailscale.

## 5. Requisitos não funcionais

- pt-BR; tema escuro; layout utilizável em 360 px e desktop.
- Navegação por teclado, foco visível, rótulos de formulário, estados sem depender só de cor; contraste WCAG AA; `prefers-reduced-motion` respeitado nas animações de jogo.
- Instantes em UTC; datas civis em America/Sao_Paulo; “hoje” calculado no servidor nesse fuso.
- Persistência no PostgreSQL do compose; `localStorage` só para conveniências de interface.
- Reenvio por falha de rede não duplica registros (UUID gerado no cliente).
- Backup diário automático (`pg_dump`, 14 cópias) e um teste de restauração antes de confiar nos dados.
- Subida com um comando (`docker compose up -d`); porta presa a `127.0.0.1`; acesso remoto só via Tailscale.
- Metas, XP e níveis não prometem aprovação; indicar limitações de amostras pequenas.

## 6. Fora do MVP

Login/multiusuário, ranking, rede social, tutor por IA, correção automática de redação, geração de questões, RAG, OCR, notificações push, calendário externo, modo offline, pagamentos, múltiplos concursos, integração com Gran/TEC/Qconcursos, hospedagem pública e timer Pomodoro (a duração é informada ao registrar).

## 7. Evoluções possíveis

Após duas semanas de uso: sessão cronometrada, registro de questões individuais, VPS com HTTPS e identidade, IA com corpus selecionado e referências (sempre como orientação, nunca nota oficial ou previsão).

## 8. Indicadores de sucesso

- v1 utilizável em 09/10/2026 com a primeira missão aberta e uma sessão registrada.
- Registro de sessão em até 2 minutos, inclusive pelo celular.
- Dados persistem após reiniciar containers e aparecem no Mac e no celular.
- Todas as sessões têm tópico ou tipo discursivo identificável.
- Após uma semana, o usuário sabe quais blocos fez, quais revisões estão pendentes e sua sequência atual sem consultar outra fonte.
- Uma exportação é restaurada em banco vazio sem perda ou duplicação.

Não definir sucesso como quantidade de funcionalidades, XP acumulado ou cumprimento permanente de 15 horas.

## 9. Decisões registradas na v2.0

| Decisão | Escolha |
|---|---|
| Gamificação | Camada derivada centrada em missão diária e metas |
| Usuários | Só o dono; sem login |
| Stack | FastAPI + React/TS + PostgreSQL |
| Execução | `docker compose` no Mac; acesso pelo celular via Tailscale |
| Repositório | Monorepo nesta pasta (`docs/`, `apps/api`, `apps/web`) |
| Ciclo | Começa em 09/10 com semana parcial; rebalancear após diagnóstico |
| Visual | Tema escuro; Chakra Petch, Inter, JetBrains Mono |
