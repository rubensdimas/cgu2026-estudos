# Regras de negócio

Versão 2.0 · 09/10/2026. Regras de jogo detalhadas em [10-gamificacao-e-rotina.md](10-gamificacao-e-rotina.md).

## R01 — Separar dado oficial de proposta pedagógica

Regras de prova pertencem a `exam_version`. Meta de 900 min, distribuição de horas, alternância e revisões pertencem ao plano do usuário. Não permitir que mudar disponibilidade altere pesos ou mínimos oficiais.

## R02 — Planejamento semanal

Gerar 15 ocorrências de blocos de 60 min para cada semana, com data civil e janela `before|middle|after`, sem hora de relógio obrigatória. Meta-base: 900 min. **Exceção da semana inicial:** se `starts_on` do plano não é segunda-feira, a primeira geração cria apenas as ocorrências de `starts_on` até a sexta daquela semana (09/10/2026: S13–S15). Cada ocorrência tem uma finalidade `specific|basic|complementary|essay`.

`pending → completed` ocorre por ação explícita e exige ao menos uma sessão vinculada. `pending → skipped` registra motivo opcional e não soma horas. Reabrir exige confirmação e não apaga sessões. Remanejar é alterar data/janela, não criar cópia. Não alterar ocorrências concluídas; criar ajuste futuro. Um template atualizado só rege semanas ainda não geradas: cada versão de template tem `effective_from` (segunda-feira) e o gerador usa a versão vigente na `week_start`. Rebalanceamento ([10](10-gamificacao-e-rotina.md) §7) cria nova versão; nunca edita a anterior.

## R03 — Sessão registrada

Duração manual inteira de 1 a 720 minutos; teto aceita treino completo de 5 h ou 3 h 30. `studied_on` não pode ser posterior a hoje (422). Data efetiva e tópicos obrigatórios, exceto discursiva, que exige `essay_kind` (`complementary|technical_case`) e permite tópicos associados. Tempo real pode divergir do planejado. Minutos reais somam uma única vez por sessão; conclusão do bloco não depende de alcançar 60 min. É possível registrar estudo extra sem ocorrência.

Até a fatia F4 existir, a rota genérica cria sessões `activity=essay` sem `essay_practice_id`, para que os blocos S14/S15 possam ser concluídos. A partir da F4, a rota de treino discursivo cria a sessão junto com o treino e pode vincular um treino a uma sessão discursiva já existente; XP de rubrica só existe com EssayPractice. Editar uma sessão exige versão atual. Excluir logicamente remove seu efeito nas métricas e revisões pendentes derivadas; histórico de revisões já concluídas permanece sinalizado como origem excluída. Bloco sem sessões ativas volta a pendente.

## R04 — Lote de questões

Registrar prova P1/P2/P3, tópico macro, data, fonte e contagens: `correct`, `wrong`, `blank`, `double_marked`. Todos são inteiros ≥0; soma deve ser igual a `total` e `total` deve ser >0. Lote não aceita contagens incompatíveis ou prova que difira da disciplina.

Peso `w`: P1/P2=1; P3=2.

- Nota líquida: `w × (correct − wrong)`.
- Taxa de acerto entre respostas válidas: `correct / (correct + wrong)`; se denominador=0, retornar `null`, nunca 0%.
- Cobertura de resposta: `(correct + wrong) / total`.
- Aproveitamento líquido do lote: `score / (w × total)`; pode ser negativo.

Guardar `answer_key_version` quando a fonte a informar. Não guardar um texto de gabarito definitivo presumido. Mudança de correção é edição versionada. No MVP, questões anuladas não são modeladas; conjuntos com anulação devem ser ajustados manualmente conforme gabarito da fonte antes de lançar as contagens.

## R05 — Lote não é prova completa

Não comparar 10 itens com mínimo oficial de 54 pontos. Mostrar nota e amostra. Em simulado completo, exigir lotes vinculados ao mesmo `simulation_id`, exatamente 40 itens P1, 40 P2 e 90 P3. Não reutilizar um lote em dois simulados. Só então calcular `objective_minima_met = P1≥8 and P2≥12 and P3≥54 and total≥78`.

Mínimos atendidos significam somente que o resultado simulado cumpriu requisitos numéricos. Nunca mostrar “aprovado na CGU”. Provas parciais não recebem projeção automática para 170 itens.

## R06 — Discursivas

Tipos `complementary` (máximo de 30 linhas e 30 pontos) e `technical_case` (60 linhas e 70 pontos). Usuário informa duração e linhas; texto digitado é opcional. Quebra visual de texto no navegador não equivale a linha manuscrita. Excesso de linhas gera alerta, sem inventar fórmula oficial de penalização.

Rubrica interna: cumprimento dos comandos, correção técnica, justificativa, organização, linguagem; níveis `needs_work|partial|adequate`. Nota manual opcional dentro de 0–30 ou 0–70, com origem `self|human_reviewer`. Não há nota automática nem nota oficial.

Somar NFPD e calcular NFC apenas quando um simulado completo tem exatamente um treino de cada tipo com nota manual. Marcar o resultado como estimativa baseada em avaliação manual. Sem ambas as notas, NFC e estado da discursiva são `null`. Minimum NFPD=50; mesmo cumprido não determina classificação oficial.

## R07 — Revisões

A revisão é **por tópico**. Ao salvar uma sessão ativa de teoria, o app cria sozinho, para cada tópico, revisões em 1, 7 e 21 dias após `studied_on`, sem etapa de aceite. Datas na prova ou depois dela ficam fora da fila. Não se cria revisão a até 2 dias de outra pendente do mesmo tópico. Cada dia comporta no máximo 3 revisões pendentes: se a data já tem 3, a revisão vai para o primeiro dos 2 dias seguintes com vaga e, depois disso, para o próximo sábado ou domingo com vaga; se não houver vaga antes da prova, ela não é criada. Excluir a sessão dispensa as pendentes dela; trocar o tópico da sessão cria revisões para o novo e dispensa as pendentes do antigo; mudar a data da sessão não recalcula as revisões. Revisões concluídas não geram outra cadeia.

Unicidade: `(session_id, topic_id, offset_days)`. Estados `pending|completed|dismissed`; atraso é derivado (`pending` com data vencida). A revisão segue um roteiro de referência de 10 min — 3 de flashcards do tópico (R16), 5 com 5 questões CEBRASPE e 2 de análise de erros sem consulta —, com questões e análise feitas fora do app. Na parte de flashcards, cada cartão aprovado recebe uma autoavaliação (`lembrei`, `parcial`, `palpite`, `nao_lembrei`); a última fica salva e ordena os cartões da próxima revisão do tópico, piores primeiro.

Concluir registra `completed_on` e fecha junto as revisões **atrasadas** do mesmo tópico, que não pontuam. Concluir não soma tempo; o app oferece registrar uma sessão "Revisão" de 10 min, opcional. Na implantação, as sessões já registradas receberam só as revisões de hoje em diante.

## R08 — Cobertura e prioridades

Estado declarado por tópico: `not_started|in_progress|first_pass|reviewed`. O usuário ajusta o estado no Edital a qualquer momento. Sessões ativas de teoria também o promovem: sessão avulsa ou em bloco concluído leva a `first_pass`; sessão em bloco não concluído leva a `in_progress`; concluir o bloco depois promove os tópicos das suas sessões de teoria a `first_pass`. A promoção só sobe nessa ordem, nunca rebaixa, e grava `declared_on` com a data do estudo. Excluir sessão, trocar tópico ou reabrir bloco não reverte o estado. Questões, revisões, discursivas e resultados de questões não alteram o estado. “Cobertura” = número de tópicos com primeira passagem ou revisado / total ativo; não é probabilidade de domínio.

Lista inicial de atenção: tópicos não iniciados, erros ainda abertos e revisões atrasadas. Resultados com menos de 20 itens válidos por tópico mostram “amostra pequena”. Esse corte é uma regra interna proposta, não limiar estatístico validado. Não misturar tentativas repetidas com contagem de questões únicas; MVP contabiliza tentativas agregadas.

## R09 — Metas e comparações

Separar planejado, realizado e concluído. Um bloco de 60 min com sessão de 45 min pode estar concluído; painel mostra 45 min reais. Sem dados, mostrar ausência de dados, não 0% de conhecimento. Semana civil começa na segunda-feira no fuso configurado (America/Sao_Paulo); a semana inicial parcial é tratada como a semana civil que a contém. Edição tardia recalcula a semana efetiva do estudo, não a semana da digitação.

## R10 — Usuário único, duplicação e conflitos

Não há identidade nem `user_id`: todo dado pertence ao único dono da instância local. Exposição fora de `127.0.0.1`/Tailscale ou uso por outra pessoa exige reintroduzir identidade antes.

Criações recebem o `id` UUID **gerado pelo cliente**. Reenviar o mesmo `id` com conteúdo igual retorna o registro original (200), sem duplicar; mesmo `id` com conteúdo diferente retorna 409. A comparação considera os campos enviados, ignorando timestamps. Edição usa `version`; versão desatualizada retorna 409 e mantém dados do servidor.

## R11 — Exportação/restauração

Exportar JSON `schema_version=2`, regras do concurso usadas, catálogo, settings, plano, templates, ocorrências, missões, folgas e registros pessoais. Não exportar senha, cookie, token ou segredos. Restaurar valida referências, tipos, contagens e versões antes de gravar. Operação atômica; IDs já existentes com conteúdo divergente causam 409; iguais são ignorados. IDs ausentes são inseridos. Não sobrescrever silenciosamente. Configurações (`settings`) são exportadas e restauradas como os demais registros. Dados de jogo não são exportados porque são derivados.

## R12 — Dados e materiais

Links e anotações pessoais são aceitos. Não coletar conteúdo de cursos pagos por automação nem pressupor acesso compartilhado. Site, edital e referências não contam como tempo de estudo. No MVP, o aplicativo depende de conexão: falha de rede conserva formulário na tela e oferece reenvio; não promete modo offline ou sincronização local.

## R13 — Missão do dia

Criada só por ação explícita para uma data civil; uma por data. Itens congelados na geração; `done` é derivado, `not_applicable` é a única marcação manual, com motivo opcional. Completa quando todos os obrigatórios estão `done`/`not_applicable` e ao menos um obrigatório está `done`. Missão de data futura não pode ser criada; de data passada pode, para registro tardio, mas não altera a sequência além do que as sessões já determinam. Detalhes em [10](10-gamificacao-e-rotina.md) §2.

## R14 — Camada de jogo derivada

XP, nível, sequência, congelamentos, conquistas, estado de metas e chefões são funções puras sobre registros ativos. Não persistir nem exportar esses valores como fonte de verdade; eventual cache é invalidado após qualquer mutação. Taxa de acerto e nota não geram XP; não existe XP negativo. Sequência conta dias úteis com ≥ 30 min; folga declarada é neutra; congelamentos conforme [10](10-gamificacao-e-rotina.md) §5.

## R15 — Metas

Metas semanais e de etapa são proposta pedagógica (R01): editáveis em `settings`, nunca alteram regras oficiais. Planejado, realizado e meta aparecem separados. Chefão é derrotado por conclusão (simulado completo, caderno limpo), nunca por nota. Sugestão de rebalanceamento exige aceite explícito e só afeta semanas não geradas.

## R16 — Flashcards gerados por IA

Só sessões ativas de teoria com tópico geram flashcards, por ação explícita ("Gerar flashcards"), inclusive sessões já registradas. O app envia à OpenAI a disciplina, o tópico, os subitens do edital do tópico, título e nota dos materiais sugeridos e o texto "O que estudei / errei" (pré-preenchido com a observação da sessão); o modelo não acessa os links. A instrução fica em `apps/api/app/flashcards/prompt.md`: banca CEBRASPE, terminologia do edital, de 5 a 10 cartões sem preencher quantidade, nada fora dos subitens e nada de dispositivo legal inventado.

Cada cartão indica o subitem que cobre; o app descarta cartões sem subitem válido e corta acima de 10. Cartões entram como rascunho: o usuário aprova, edita ou descarta; só aprovados formam o baralho. Gerar de novo substitui apenas os rascunhos da sessão. Falha ou demora (60 s) não grava nada. Sem `OPENAI_API_KEY`, a geração fica desligada. Excluir a sessão mantém os cartões aprovados. Cartões são apoio de revisão, não avaliação de domínio.
