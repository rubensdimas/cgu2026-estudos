# Base do edital e plano inicial

Versão 2.0 · 09/10/2026.

## 1. Perfil versionado do concurso

Fonte: PDF enviado, item 4.1, itens 7/8.11/9/11.1 e Anexo I. Identificador interno: `cgu-2026-affc-dev`; versão: `edital-2026-10-08-v1`.

| Campo | Valor no PDF |
|---|---|
| Cargo | AFFC — TI — Desenvolvimento de Sistemas, Cargo 4 |
| Vagas da especialidade | 10, dentro de 30 vagas distribuídas nas três especialidades de TI |
| Lotação | Órgão Central — DF |
| P1 | 40 itens, +1/−1, máximo 40, mínimo 8 |
| P2 | 40 itens, +1/−1, máximo 40, mínimo 12 |
| P3 | 90 itens, +2/−2, máximo 180, mínimo 54 |
| Total objetivo | 170 itens, máximo 260, mínimo 78 |
| Discursiva | 30 pontos/até 30 linhas + 70 pontos/até 60 linhas; mínimo total 50 |
| Classificação | `NFC = NFPO / 26 + NFPD / 10` |
| Provas previstas | 13/12/2026; objetivas 5 h pela manhã e discursiva 3 h 30 à tarde |
| Inscrição | 10/10 a 4/11/2026, 10 h do primeiro dia até 18 h do último |
| Pagamento | Até 6/11/2026; taxa de R$ 170 |

Verificação em 09/10/2026: o arquivo [`edital.pdf`](edital.pdf) deste repositório tem SHA-256 `869d4a42…2aee7`, idêntico ao registrado na v1. Busca por retificações no DOU, no Cebraspe e em portais de notícias não localizou nenhuma; a página do Cebraspe não exibiu conteúdo à consulta automatizada. Repetir a verificação manualmente antes de cada etapa.

Os mínimos objetivos são simultâneos. Atendê-los não garante correção da discursiva: há limites de classificação por modalidade/lotação no edital. O MVP não calcula posição, chances de aprovação ou vagas por modalidade.

## 2. Catálogo de conteúdos

| Código | Prova | Disciplina |
|---|---|---|
| B01 | P1 | Estado, democracia, direitos e ciência política |
| B02 | P1 | Sociedade brasileira, desigualdades, diversidade e desenvolvimento |
| B03 | P1 | Ética pública e responsabilidade profissional |
| B04 | P1 | Administração pública e fundamentos de políticas públicas |
| C01 | P2 | Fundamentos de governança, riscos e integridade pública e privada |
| C02 | P2 | Fundamentos de transparência, ouvidoria e participação social |
| C03 | P2 | Fundamentos de direito público aplicado, controle e responsabilização |
| C04 | P2 | Fundamentos de evidências, dados e inteligência artificial |
| C05 | P2 | Fundamentos de auditoria governamental e atuação integrada da CGU |
| E01 | P3 | Engenharia de software e programação |
| E02 | P3 | Arquitetura e integração de sistemas |
| E03 | P3 | Persistência, integração e proteção de dados |
| E04 | P3 | Desenvolvimento seguro, qualidade e gestão da entrega |

`catalogo-edital.json` contém esses grupos e os 68 tópicos macro. Cada tópico tem ID estável e referência ao bloco/numeração do edital. Seus títulos são resumos editoriais. Os subitens detalhados, como 2.3 e 2.4, devem ser consultados no PDF ou adicionados posteriormente com revisão humana.

Português não aparece como disciplina autônoma no programa do PDF. Escrita e gramática entram no treino de discursivas; Constitucional e Administrativo devem seguir o recorte de conhecimentos gerais, sem importar programa de outro concurso.

## 3. Ciclo-base

### A partir de 26/10/2026: 1 tópico por dia

O ciclo de 3 blocos diários não se sustentou na rotina. Desde 26/10 cada dia útil tem **1 bloco de 60 min** e até 30 min de revisões (3 × 10 min, [03](03-regras-de-negocio.md) R07). Template em [`ciclo-2026-10-26.json`](data/ciclo-2026-10-26.json), 300 min por semana.

| Dia | Bloco de 60 min | Rodízio por semana (desde 26/10) |
|---|---|---|
| Segunda | Específica | E01 → E03 |
| Terça | Complementares (P2) | C01 → C02 → C03 → C04 → C05 |
| Quarta | Específica | E02 → E04 |
| Quinta | Básicos (P1) | B01 → B02 → B03 → B04 |
| Sexta | Discursiva | complementar → situação-problema |

O app sugere o primeiro tópico da disciplina da semana ainda sem primeira passagem declarada antes do dia do bloco; disciplina esgotada passa à seguinte da lista. O usuário confirma o tópico efetivamente estudado. Na virada, o comando `python -m app.replan` dispensou os blocos pendentes de 21–25/10 e recriou as revisões dos tópicos já estudados nos fins de semana (31/10–01/11, 07–08/11 e 21–22/11).

### Até 25/10/2026: 3 blocos por dia

| Dia | Antes — 60 min | Intermediário — 60 min | Depois — 60 min |
|---|---|---|---|
| Segunda | B01/B02 | Questões E01 | E01 |
| Terça | C01/C02 | Questões E02 | E02 |
| Quarta | B03/B04 | Questões E03 | E03 |
| Quinta | C03/C05 | Questões de P1 | E04 ou Vue.js/IA |
| Sexta | C02/C04 + revisão da semana | Discursiva complementar | Situação-problema de TI |

**Início em 09/10/2026 (sexta):** a primeira semana é parcial e contém apenas os blocos de sexta (S13, S14, S15 = 180 min). A partir de 12/10 a semana segue o ciclo completo.

Distribuição por finalidade: específicos 420 min; básicos 180 min; complementares 180 min; discursivas 120 min. Não somar a sessão discursiva duas vezes nas horas gerais. Nos relatórios de conteúdo ela pode ser associada a uma disciplina, mas sua finalidade continua sendo discursiva.

Alternâncias propostas: nos blocos com duas disciplinas, semanas ímpares usam a primeira e pares a segunda. Quinta à noite: semanas ímpares E04, pares E01.04 (interfaces) ou E02.04 (dados/IA), escolhido manualmente. O bloco geral de questões de quinta roda B01→B02→B03→B04 por semana. O sistema sugere; o usuário confirma o tópico efetivamente estudado.

## 4. Etapas de preparação

| Período (inclui fim de semana seguinte) | Foco | Entrega de estudo | Chefão |
|---|---|---|---|
| 09–25/10 | Diagnóstico e primeira passagem | Lacunas identificadas, questões por P1/P2/P3 e primeiras discursivas | Simulado diagnóstico completo |
| 26/10–22/11 | Aprofundamento | Java/Spring/JPA/Batch, Vue/IA, segurança, contratos e funções da CGU | Segundo simulado + discursivas |
| 23/11–06/12 | Consolidação | Conjuntos mistos, nota líquida e respostas completas cronometradas | Simulado em condições de prova |
| 07–12/12 | Revisão final | Erros, sínteses, logística e manutenção do ritmo | Caderno limpo |

Metas de cada etapa e regras dos chefões: [10-gamificacao-e-rotina.md](10-gamificacao-e-rotina.md) §6.

Planejamento: semana parcial de 180 min, duas semanas de 900 min (12–25/10) e, a partir de 26/10, semanas de 300 min, antes de faltas e escolhas sobre feriados. O sistema não supõe estudo em feriado nem retira dias automaticamente: o usuário confirma a agenda. 12/12 reservado inicialmente para descanso/logística.

## 5. Prioridades de diagnóstico

Java e concorrência; Spring Boot/Security; JPA/Spring Data JPA; Spring Batch; Vue.js e acessibilidade; integração de IA com autorização e proteção contra instruções externas; dados e transações; funções da CGU; governança e auditoria; contratação e fiscalização; escrita.

Engenharia de Software é a base mais forte do usuário: espera-se partida melhor em requisitos, arquitetura, testes, APIs e SQL do que nos itens Java/Spring/Vue e nas provas P1/P2. Por isso a distribuição 420/180/180/120 é mantida até o simulado diagnóstico e depois rebalanceada com dados ([10-gamificacao-e-rotina.md](10-gamificacao-e-rotina.md) §7).

Prioridades são hipóteses baseadas no histórico profissional, não pesos oficiais por assunto. Atualizar após resultados, sem usar experiência prática como indicador automático de domínio.

## 6. Política de atualização

Guardar URL, PDF de referência, hash e data da versão. Uma retificação cria nova versão; registros antigos continuam associados à versão usada. Antes de publicar mudança de data, pontuação ou conteúdo, comparar manualmente com fonte oficial. Não há monitoramento automático no MVP.
