# Validação, riscos e definição de pronto

Versão 2.0 · 09/10/2026.

## Testes de regras críticos

| Caso | Entrada | Resultado esperado |
|---|---|---|
| Nota P3 | 6 corretas/4 erradas/10 total | 4 pontos, taxa 60%, aproveitamento líquido 20% |
| Nota negativa | P1, 2 corretas/8 erradas | −6 pontos; não truncar para zero |
| Nenhuma resposta | 10 em branco | 0 pontos, taxa de acerto null |
| Entrada inválida | total 10, contagens somando 11 | 422; nada salvo |
| Simulado limítrofe | P1:24/16; P2:26/14; P3:54/27/9 branco | 8,12,54; soma74: falha no mínimo total |
| Simulado com mínimos | P1:26/14; P2:26/14; P3:54/27/9 branco | 12+12+54=78: mínimos numéricos atendidos |
| NFC pessoal | NFPO260, discursivas30+70 | 20; indicar estimativa manual |
| Discursiva incompleta | Apenas nota técnica | NFPD/NFC indisponíveis |
| Intervalos | Estudo 12/10 | Revisões 13/10,19/10,2/11 |
| Revisão além da prova | Estudo 1/12, intervalo21 | Não entra na fila de preparação |
| Prova parcial | 10 itens P3 | Sem indicador de mínimo54 atendido/falhado |
| Reenvio | Mesmo `id` e conteúdo duas vezes | Um registro, mesma resposta |
| Conflito | Mesmo `id` com outro conteúdo | 409; preservar original |
| Concorrência | PATCH version1 após versão2 | 409 |
| Tempo discursivo | Treino60 min com sessão associada | 60 min, não120 |
| Exclusão | Sessão com revisão pendente | Excluir efeito e dispensar fila derivada; preservar auditabilidade |
| Semana duplicada | Gerar mesma semana duas vezes | 15 ocorrências, não30 |
| Importação inválida | Referência de tópico inexistente | Sem escrita parcial |
| Semana inicial | Plano inicia sexta 09/10 | 3 ocorrências (S13–S15), 180 min |
| Missão repetida | Abrir o dia 2× | Uma missão |
| Missão vazia | Todos os itens “não se aplica” | Incompleta, sem bônus |
| XP com teto | 300 min num dia | 240 XP de minutos |
| XP derivado | Excluir sessão que concluiu bloco | XP do bloco e dos minutos some; bloco pendente |
| Acerto sem XP | Lote 10/0 vs 0/10 | Mesmo XP (+10) |
| Nível | 300 XP · 15.300 XP | Nv 3 · Nv 18 “AFFC” |
| Sequência quebrada | Dia útil 0 min, sem congelamento | Sequência 0, recorde preservado |
| Folga | Dia útil marcado como folga | Neutro: não quebra nem conta |
| Fim de semana | Sábado sem estudo | Não quebra |
| Hoje em jogo | Hoje com 10 min | `at_stake_today`, sequência inalterada |
| Congelamento | Semana completa e dia útil vazio seguinte | Congelamento consumido; sequência mantida |
| Chefão | Simulado 40/40/90 com nota baixa | Chefão derrotado (conclusão, não nota) |
| Rebalanceamento | Folgas P1 0,10 · P2 0,20 · P3 0,256 | Sugere 1 bloco specific → basic; não aplica sem aceite |

Nas contagens do simulado, formato é corretas/erradas, com branco quando mencionado. Validar somas antes de comparar notas.

## Testes de integração

Banco `cgu_test` isolado. Testar migração e seed duas vezes; reinício do compose preservando volume; transações de treino/sessão; conflito de importação; persistência após nova conexão. Regras puras recebem testes unitários; fluxo crítico recebe integração com API/banco. Não escrever testes que apenas repetem textos estáticos.

## QA de interface

Uma jornada completa por cenário principal: gerar semana, abrir o dia, missão, sessão, lote/erro, revisão, discursiva, painel e exportação. Conferir celular 360 px, desktop, teclado, foco e ampliação de texto. Falha de rede não limpa formulário; erro de servidor não produz sucesso falso. Não preencher dashboards com histórico inventado.

## Riscos e respostas

| Risco | Tratamento |
|---|---|
| Construir durante a preparação consome horas de estudo | Limitar MVP, entregar fluxo útil primeiro e continuar usando site atual |
| Regras do edital alteradas | Versão e referência; revisão manual antes de atualização |
| Uso de métricas parciais como aprovação | Bloquear comparação com mínimos sem conjunto40/40/90 |
| Baixa amostra ou repetição | Exibir contagem e usar “tentativas”, não “questões únicas” |
| Cobertura interpretada como domínio | Estado declarado e indicadores separados |
| IA fornece certeza ou nota fictícia | IA fora do MVP; fase posterior com fontes e rótulos |
| Conteúdo pago reproduzido | Guardar apenas referências e anotações pessoais |
| Perda de dados | Exportação, backups e teste de restauração |
| Dependência do bloco no trabalho | Remanejamento sem horário obrigatório |
| Infra diferente da página atual | Não reutilizar host estático como se executasse FastAPI |
| Gamificação incentiva inflar registros | XP derivado com tetos diários; acerto não dá XP; “XP mede constância, não preparo” |
| Sequência vira fonte de ansiedade | Fim de semana neutro, folgas declaráveis, congelamentos, sem XP negativo |
| Jogo confundido com preparo | Nível e título decorativos; métricas de desempenho separadas |
| App sem login exposto | Porta em 127.0.0.1; só `tailscale serve`, nunca `funnel`; Postgres sem porta |
| Mac desligado impede uso no celular | Limitação aceita; registrar com data passada depois; VPS como evolução |
| Construção atrasa estudo | v1 mínima no dia 1; fatias com alvo; estudar pelos documentos se atrasar |

## Definição de pronto do MVP

- [ ] Dados iniciais importados sem duplicação: 13 disciplinas/ 68 tópicos/ 15 slots.
- [ ] Porta presa a 127.0.0.1; acesso remoto somente via `tailscale serve`.
- [ ] Jornada “abrir o dia → registrar sessão → ver XP” utilizável no Mac e no celular (PWA).
- [ ] XP, nível, sequência, metas e conquistas recalculam após editar/excluir registros.
- [ ] Geração/remanejamento/conclusão sem perda de histórico.
- [ ] Questões e discursivas respeitam diferenças de avaliação.
- [ ] Revisões e painel seguem as regras e não duplicam tempo.
- [ ] Exportação/restauração testadas com dados reais de teste.
- [ ] Casos críticos acima passando; build e migrações verificados.
- [ ] Logs sem texto de discursivas; `.env` fora do Git; backup diário com restauração ensaiada.
- [ ] Referência do edital e caráter proposto do plano visíveis.

## Validação em uso

Primeira semana: testar registro rápido e completar uma jornada por dia. Segunda: avaliar se os dados ajudam a escolher revisão e lacunas. Só então escolher uma próxima funcionalidade. Não transformar custo de uso ou preenchimento em mais trabalho que o estudo.
