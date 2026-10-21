# Rotina diária gamificada

Versão 2.0 · 09/10/2026. Configuração carregável em [data/gamificacao.json](data/gamificacao.json).

## 1. Princípios

- A gamificação existe para **sustentar a rotina diária**: abrir o dia, cumprir a missão, manter a sequência e alcançar as metas. Ela é uma camada sobre os registros; não altera regras oficiais (R01) nem métricas de desempenho (R04–R09).
- **Tudo é derivado.** XP, nível, sequência, congelamentos, conquistas e estado de metas são calculados a partir de sessões, ocorrências, missões, lotes, erros, revisões, discursivas e simulados. Nada disso é persistido como fonte de verdade; editar ou excluir um registro recalcula o resultado.
- **Recompensa esforço e constância, nunca acerto.** Taxa de acerto e nota líquida aparecem nas métricas, separadas do XP, para não incentivar fuga de assuntos difíceis ou brancos estratégicos.
- **Sem perda de XP e sem punição.** Falta aparece como bloco pendente ou sequência interrompida, nunca como XP negativo.
- **Sem promessa.** Nenhum elemento de jogo sugere aprovação, posição ou chance (R05, R09).

## 2. Missão do dia

### Geração

A missão de uma data civil é criada por ação explícita “Abrir o dia” (`POST /days/{date}/mission`). Se a semana daquela data ainda não foi gerada, a mesma ação a gera na mesma transação (um botão só). Consultar o dia nunca grava. Repetir a ação devolve a missão existente. Datas futuras são recusadas. Depois de gerada, a lista de itens fica **congelada**; mudanças no ciclo não acrescentam itens, apenas alteram o estado dos itens existentes.

### Itens (dias úteis)

| Ordem | Item | Origem | Obrigatório | Concluído quando |
|---|---|---|---|---|
| 1 | Blocos do dia (até 3) | **Todas** as ocorrências planejadas para a data, inclusive já concluídas (registrar antes de abrir o dia não pode sumir com o bloco); dispensadas entram como `not_applicable` | Sim | Ocorrência `completed` com data de conclusão ≤ data da missão |
| 2 | Revisão vencida (até 1) | `ReviewTask` pendente com `due_on ≤ data`, a mais antiga | Sim | Revisão `completed` até a data da missão |
| 3 | Meta de questões | Padrão 20 itens; tópico sugerido = tópico estudado no dia ou tópico com menor taxa de acerto e amostra ≥ 20 | Não (bônus) | Soma de `total` dos lotes da data ≥ meta |
| 4 | Check-out do dia | Uma linha: “O que ficou difícil hoje?” | Não (bônus) | Texto salvo |

Estados de item: `pending | done | not_applicable`. O usuário pode marcar qualquer item como **não se aplica hoje** (ex.: bloco intermediário indisponível), com motivo opcional, sem penalidade. Item de bloco cuja ocorrência foi remanejada para outra data vira `not_applicable` com motivo `rescheduled`; item de revisão dispensada vira `not_applicable` com motivo `dismissed`. Os estados `done` são derivados dos registros; `not_applicable` é a única marcação manual.

Enquanto a fatia de questões (F2) não existir, a missão contém blocos, revisão e check-out.

### Conclusão

Missão **completa** = todos os itens obrigatórios estão `done` ou `not_applicable` **e** ao menos um item obrigatório está `done`. Uma missão em que tudo foi marcado “não se aplica” não conta como completa.

### Blocos fora da missão e atrasados

A missão é uma foto tirada ao abrir o dia e não muda depois. Bloco que entra no dia depois disso (remanejado ou trazido de dia passado) aparece em **Outros blocos de hoje**: dá XP e conclui o bloco, mas não conta para a missão. Blocos pendentes de dias anteriores aparecem num aviso de **atrasados**, e o usuário escolhe quais trazer para hoje. Detalhes: [spec de 10/10](superpowers/specs/2026-10-10-blocos-e-orientacoes.md).

### Fim de semana: missão livre

Sábado e domingo não têm ciclo. “Abrir o dia” num fim de semana cria uma **missão livre**: o usuário escolhe até 4 revisões vencidas (as 4 mais antigas vêm marcadas) e até 2 blocos pendentes da semana; pode abrir só com revisões (que são remanejados para a data); meta de questões e check-out entram como opcionais. Estudo fora da missão é registrado como sessão avulsa. A conclusão segue a mesma regra e rende o XP normal, mas não é exigida pela sequência.

## 3. XP

Todo XP é atribuído à **data civil do evento** (`studied_on`, `practiced_on`, `completed_on`, data da missão).

| Evento | XP | Limite |
|---|---|---|
| Minuto real de sessão ativa | 1 por minuto | 240 por dia |
| Bloco do ciclo concluído | +20 | — |
| Missão do dia completa | +50 | 1 por dia |
| Item opcional da missão concluído (questões, check-out) | +10 cada | — |
| Item de questão em lote (`total`) | +1 por item | 200 por dia |
| Erro anotado no caderno | +10 | 100 por dia |
| Revisão concluída até `due_on` | +15 | Atrasadas fechadas junto não pontuam |
| Revisão concluída após `due_on` | +5 | — |
| Discursiva com rubrica completa — complementar | +40 | — |
| Discursiva com rubrica completa — situação-problema | +60 | — |
| Simulado objetivo completo (40/40/90) | +150 | — |
| Chefão de etapa derrotado | +100 | 1 por etapa |
| Semana completa | +150 | 1 por semana |
| Dia de fim de semana com ≥ 30 min | +20 | — |

Os valores são uma proposta inicial do produto e ficam em `gamificacao.json`. Registros excluídos logicamente não geram XP. O XP de sessões de discursiva conta como minutos normais; a discursiva soma o bônus de rubrica só uma vez.

**Data do XP de bloco:** data de conclusão derivada = maior `studied_on` entre as sessões ativas vinculadas.

**Semana completa:** todas as ocorrências da semana estão `completed` (dispensadas não contam como concluídas) **ou** os minutos reais da semana alcançam a meta semanal de minutos.

## 4. Nível e títulos

Subir do nível *n* para *n+1* exige `100 × n` XP. XP acumulado para estar no nível *L*: `50 × L × (L − 1)`.

| Níveis | Título |
|---|---|
| 1–3 | Estagiário |
| 4–7 | Analista |
| 8–12 | Auditor Júnior |
| 13–17 | Auditor |
| 18+ | AFFC |

Referência: executar o ciclo completo por 9 semanas, com missões e questões, gera da ordem de 15–20 mil XP, ou seja, nível 18–20 perto da prova (nível 18 = 15.300 XP acumulados). O título é decorativo; não representa preparo.

## 5. Sequência

- Conta **dias úteis** (segunda a sexta). Um dia útil é **ativo** se a soma de minutos de sessões ativas com aquela `studied_on` for ≥ 30.
- Sábado e domingo nunca quebram a sequência e nunca a aumentam; estudar neles rende o bônus da tabela de XP.
- **Folga declarada** (`DayOff`: feriado, doença, compromisso) é neutra: não quebra nem conta. Marcar e desmarcar é livre; o cálculo é refeito. Os feriados nacionais em dias úteis do período (12/10, 02/11 e 20/11/2026, em `gamificacao.json`) aparecem como **sugestão** de folga na véspera; nada é marcado automaticamente, porque o usuário pode preferir estudar.
- **Congelamento:** cada semana completa concede 1 congelamento, com estoque máximo de 2. Um dia útil passado não ativo e não declarado como folga consome automaticamente um congelamento, se houver; sem congelamento, a sequência é zerada.
- O dia de hoje só é avaliado depois de encerrado: enquanto ele não terminar, a sequência exibe “em jogo hoje”.
- Cálculo determinístico: percorrer os dias úteis em ordem desde o início do plano, aplicando ganhos de congelamento no fim de cada semana completa e consumos na ordem dos dias perdidos. Exibir sequência atual, recorde e congelamentos disponíveis.

## 6. Metas

### Semanais

Padrões (editáveis em Configurações, sem alterar regras oficiais):

| Meta | Padrão |
|---|---|
| Minutos reais | 900 |
| Blocos concluídos | 15 |
| Itens de questões P1 / P2 / P3 | 40 / 40 / 90 |
| Discursivas com rubrica | 1 complementar + 1 situação-problema |
| Missões completas | 5 |

Cada meta mostra planejado × realizado e nunca preenche ausência de dados com zero de conhecimento (R09). Blocos contam na semana da ocorrência (`week_start`), mesmo se remanejados; minutos, questões e discursivas contam na semana da data efetiva do registro.

Se o bloco intermediário ficar indisponível de forma recorrente, a semana só fica completa pelos minutos. Nesse caso, ajustar a meta semanal de minutos em Configurações ou remanejar os blocos para outra janela, em vez de acumular dispensas.

**Semana inicial parcial** (09–11/10/2026): metas proporcionais às ocorrências geradas: 180 min, 3 blocos, 1 missão, 2 discursivas (S14/S15 de sexta) e questões P1/P2/P3 = 8/8/18 (1/5 da meta, arredondado).

### Etapas e chefões

As etapas de [02-edital-e-plano.md](02-edital-e-plano.md) §4 viram fases do jogo. Fins de semana pertencem à etapa anterior. O **chefão** de cada etapa é um objetivo concreto; derrotá-lo depende de completar, nunca de nota.

| Etapa | Período | Metas da etapa | Chefão |
|---|---|---|---|
| 1. Diagnóstico | 09/10–25/10 | 13 disciplinas com ≥ 1 sessão; ≥ 1 discursiva de cada tipo; 200 itens de questões | Simulado diagnóstico completo (40/40/90) |
| 2. Aprofundamento | 26/10–22/11 | ≥ 70% dos tópicos em `first_pass` ou `reviewed`; 600 itens; 4 discursivas | Segundo simulado completo + 1 discursiva de cada tipo vinculada |
| 3. Consolidação | 23/11–06/12 | ≥ 90% de cobertura declarada; 0 revisões atrasadas ao fim; 2 respostas discursivas completas cronometradas | Simulado completo em condições de prova (5 h objetivas + 3 h 30 discursivas, mesmo dia) |
| 4. Revisão final | 07/12–12/12 | Todos os erros do caderno revisados ou resolvidos; revisões vencidas zeradas | “Caderno limpo”: 0 erros abertos sem revisão e 0 revisões atrasadas em 11/12 |

12/12 é descanso/logística e 13/12 é a prova: a contagem regressiva termina aí.

### Marcos do concurso

Exibidos junto à contagem regressiva, como lembretes visuais sem notificação: inscrição de 10/10 (10 h) a 04/11/2026 (18 h); pagamento da taxa até 06/11/2026; provas em 13/12/2026.

## 7. Rebalanceamento após o diagnóstico

Ao derrotar o chefão da etapa 1, o app calcula uma **sugestão** de rebalanceamento do ciclo a partir do simulado diagnóstico:

1. Aproveitamento relativo por prova: `score / máximo` (P1/40, P2/40, P3/180).
2. Folga sobre o mínimo: `(score − mínimo) / máximo`.
3. A finalidade com maior folga cede **1 bloco de 60 min** para a finalidade com menor folga (mapa: P1→`basic`, P2→`complementary`, P3→`specific`). No máximo 2 blocos por rebalanceamento; `specific` nunca fica abaixo de 300 min; `essay` não participa.
4. O usuário aceita, ajusta ou recusa. Aceitar cria uma nova versão do template que vale **só para semanas ainda não geradas** (R02).

A sugestão é uma heurística de produto, não uma recomendação estatística. A mesma tela pode ser usada manualmente em qualquer momento.

## 8. Conquistas

Todas derivadas. A data de desbloqueio é a data do evento que cumpriu a condição.

| ID | Nome | Condição |
|---|---|---|
| A01 | Primeiro passo | Primeira sessão registrada |
| A02 | Missão cumprida | Primeira missão completa |
| A03 | Madrugador | 10 blocos da janela `before` concluídos |
| A04 | Em chamas | Sequência de 5 dias úteis |
| A05 | Imparável | Sequência de 20 dias úteis |
| A06 | Semana cheia | Primeira semana completa |
| A07 | Panorama | 13 disciplinas com ≥ 1 sessão |
| A08 | Centena técnica | 100 itens de P3 |
| A09 | Milhar | 1.000 itens de questões |
| A10 | Caçador de erros | 25 erros anotados |
| A11 | Memória em dia | 20 revisões concluídas no prazo |
| A12 | Escriba | 5 discursivas com rubrica |
| A13 | Caso resolvido | 5 situações-problema com rubrica |
| A14 | Primeiro chefão | Primeiro simulado objetivo completo |
| A15 | Campanha completa | 4 chefões derrotados |
| A16 | Edital mapeado | 100% dos tópicos em `first_pass` ou `reviewed` |

Cada conquista só aparece quando a fatia que produz seus dados existir.

## 9. Interface do jogo

- **HUD fixo** no topo: nível e título, barra de XP do nível, chama da sequência com número e congelamentos, contagem regressiva “D-65”.
- **Hoje**: anel de progresso da missão (itens obrigatórios), lista de itens com ação direta e XP ganho no dia.
- **Feedback**: ao salvar, toast com o XP ganho (“+45 XP · bloco concluído”). Subida de nível e conquista mostram cartão próprio, dispensável, respeitando `prefers-reduced-motion`.
- **Jornada**: linha das 4 etapas com metas, chefões e marcos do concurso.
- **Conquistas**: grade com conquistas bloqueadas visíveis (condição exibida) e desbloqueadas com data.
- Detalhes visuais em [06-ux-e-fluxos.md](06-ux-e-fluxos.md).
