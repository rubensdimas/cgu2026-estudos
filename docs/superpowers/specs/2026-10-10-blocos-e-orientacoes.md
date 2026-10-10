# Blocos remanejados e orientações por bloco — spec

Data: 10/10/2026. Origem: grilling de 10/10/2026 (rodadas registradas na conversa). Base: [10-gamificacao-e-rotina.md](../../10-gamificacao-e-rotina.md), [02-edital-e-plano.md](../../02-edital-e-plano.md), edital item 9.

## Problema

1. A missão do dia é uma foto tirada ao abrir o dia (`open_day`). Bloco que entra no dia depois disso não aparece em lugar nenhum para registrar sessão.
2. Blocos esquecidos em dias passados ficam pendentes na data antiga sem aviso.
3. Os cards só mostram o título do bloco. "Complementares e revisão" não explica o que fazer, e S14/S15 (discursivas) não trazem tema, caso nem formato. O usuário perde minutos do bloco pesquisando.

## Parte A — blocos remanejados

- **A1. "Outros blocos de hoje"**: com a missão aberta, a tela Hoje lista os blocos com `planned_on = hoje` que não são itens da missão. Pendentes têm "Registrar sessão" e "Mover para amanhã"; concluídos aparecem com ✓; dispensados não aparecem. Dão XP e concluem o bloco normalmente, mas **não contam** para "Missão cumprida". A missão continua uma foto fixa. Sem missão aberta, a seção não aparece.
- **A2. Missão livre**: limite de 2 blocos mantido.
- **A3. "Mover para amanhã"**: atalho na linha do bloco pendente (itens da missão e "Outros blocos"). Move para `hoje + 1` literal (sexta → sábado), mantém a janela, usa `PATCH /occurrences/{id}`. Some se `hoje + 1` passar de `plan.ends_on`.
- **A4. Aviso de atrasados**: no topo da tela Hoje, conta blocos `pending` com `planned_on < hoje`, de qualquer semana do plano. Abre lista com checkbox; os marcados vão para hoje mantendo a janela; os outros ficam. Sem botão de fechar: some quando não houver atrasados.

Fora do escopo: missão mutável, mover automaticamente, mudar o limite de 2.

## Parte B — orientações por bloco

- **B1. Fonte**: `docs/data/orientacoes.json`, versionado, com fontes citadas. Sem IA no app.
- **B2. Card**: painel "Como fazer este bloco" (tela Hoje e tela Ciclo) com roteiro (passos com minutos), tópico sugerido com subitens literais do edital e 1–3 materiais oficiais.
- **B3. S13** passa a se chamar **"Complementares + revisão da semana"**: ≈45 min no tópico novo + ≈15 min revisando as anotações da semana; na semana parcial (índice 0), 60 min no tópico.
- **B4. S14 (Q1)** e **S15 (Q2)** no formato Cebraspe (edital 9.1 e 9.7):
  - Q1: complementares, até 30 linhas, 30 pontos. Q2: situação-problema dos específicos, até 60 linhas, 70 pontos.
  - Enunciado: texto motivador + comando + aspectos numerados com valor (somam 30 ou 70).
  - Espelho: texto-padrão + quesitos 2.x com conceitos 0 a N; escondido até "Ver pontos esperados".
  - Lembretes do edital: limite de linhas, fuga ao tema zera, NQ1 = NC − 6·NE/TL e NQ2 = NC − 14·NE/TL, NFPD ≥ 50.
  - "Semelhante à prova X" só com fonte real.
  - Temas de S14 rodam entre C01–C05; casos de S15 entre E01–E04 + contratação de TIC e LGPD, puxando para Java/Spring, segurança e IA.
- **B5. S15 reduzido até 22/11/2026**: 15 min de esquema de todos os aspectos + 40 min escrevendo 2 aspectos (~30 linhas) + 5 min de revisão. A partir de 23/11, roteiro de resposta completa cronometrada (Etapa 3).
- **B6. Rodízio de temas**: um tema por semana pelo índice da semana; "Trocar tema" vai para o próximo ainda não feito; tema conta como feito quando há sessão no bloco, e a partir daí fica fixo.
- **B7. Volume inicial**: roteiros por atividade + S13/S14/S15; subitens dos 68 tópicos; materiais dos tópicos sugeridos de 12/10 a 25/10; ~10 temas S14 e ~10 casos S15.
- **B8. Revisão**: temas e casos passam por um documento para o usuário revisar antes de entrarem no JSON; roteiros e subitens pelo diff.
- **Fica para a F4**: autoavaliação pelo espelho, cálculo de NQ, rubrica e XP de rubrica.
