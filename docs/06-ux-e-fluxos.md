# UX e jornadas

Versão 2.0 · 09/10/2026.

## Direção visual

Versão 2.1 (10/10/2026): identidade inspirada na **BeroLab** (berolab.app; também referência do yurirdev.com). Grafite levemente tingido, roxo lavanda nas ações, dourado no XP, bordas finas translúcidas, tipografia Inter com detalhes monoespaçados e pixel no HUD. Tema escuro único. O app abre direto em **Hoje**.

Os tokens seguem os nomes semânticos do **shadcn** (`src/index.css`), base para os componentes do **Trophy UI** (ui.trophy.so, MIT), copiados para `src/components/ui/` e traduzidos para pt-BR.

### Tokens de cor (contraste AA)

| Token | Valor | Uso |
|---|---|---|
| `background` | `#161718` | Fundo da página |
| `card` / `popover` | `#1b1c1d` | Cartões, diálogos |
| `muted` / `secondary` | `#232525` | Superfícies elevadas, inputs |
| `accent` | `#363737` | Hover |
| `border` / `input` | branco 10% / 16% | Divisórias, campos |
| `foreground` | `#eeeeee` | Texto principal |
| `muted-foreground` | `#919191` | Texto secundário |
| `primary` / `ring` | `#b78cf2` (texto `#161718`) | Ações, item ativo, foco |
| `xp` | `#f2c94f` | XP, nível, D-n |
| `streak` | `#fb923c` | Sequência |
| `info` | `#54a2ff` | Congelamento |
| `success` / `destructive` | `#22c55e` / `#f87171` | Concluído / erro |
| P1 / P2 / P3 | `#54a2ff` / `#ffb96d` / `#00d294` | Identificação de prova, sempre com rótulo |

Cor nunca é o único sinal: estados também usam ícone e texto.

### Tipografia

| Família | Uso |
|---|---|
| **Inter** 400–700 (`@fontsource/inter`) | Títulos, texto, formulários |
| **Fira Mono** 400/500 (`@fontsource/fira-mono`) | Números, códigos de tópico, rótulos em caixa alta com `tracking-widest` |
| **Departure Mono** (auto-hospedada em `public/fonts/`, licença junto) | Só HUD (nível, título, D-n) e a marca "CGU 2026" |

Texto principal ≥ 16 px; rótulos ≥ 14 px.

### Componentes Trophy em uso

`points-badge` (XP no HUD, a partir de 640 px), `streak-card` e `streak-calendar` (com estado **neutro** para fim de semana e folga), `points-chart` (XP acumulado com linhas do nível atual e do próximo), `points-levels-timeline` (faixas de título) e `achievement-unlocked` (diálogo de subida de nível). Conquistas (`achievement-*`) entram na F5; placares não se aplicam.

### Movimento

Barra de XP e anel da missão animam ao mudar (≤ 400 ms). Subida de nível abre o diálogo `achievement-unlocked` (“Nível N · Título”, botão Continuar, fecha com Esc). Com `prefers-reduced-motion`, sem animação: só troca de estado.

## Estrutura

**HUD fixo** (todas as telas): `Nv 4 · Analista` + barra de XP do nível · 🔥 sequência (+ ❄ congelamentos) · `D-65` até a prova. No celular, o HUD é compacto, em uma linha.

| Tela | Conteúdo e ação principal | Fatia |
|---|---|---|
| Hoje | Abrir o dia, anel da missão, itens com ação direta, XP do dia; Registrar sessão | F1 |
| Ciclo | Semana em lista por dia/janela; remanejar, concluir, dispensar; gerar semana | F1 |
| Edital | P1/P2/P3, disciplinas, tópicos, referência; declarar progresso | F1 |
| Prática | Lotes e caderno de erros | F2 |
| Metas | Metas da semana (planejado × realizado) | F2 |
| Revisões | Vencidas/hoje/futuras; concluir ou dispensar | F3 |
| Discursivas | Tipos, limites, rubrica; registrar treino | F4 |
| Jornada | Etapas, metas da etapa, chefões, marcos do concurso, rebalanceamento | F4 |
| Progresso | Sequência (card + calendário mensal), XP acumulado, trilha de níveis | F1 (v2.1) · F5 (horas, cobertura, simulados) |
| Conquistas | Grade bloqueadas/desbloqueadas | F5 |
| Configurações | Metas, folgas, versão do edital, exportar/restaurar | F1 (básico) · F5 (portabilidade) |

Desktop: navegação lateral com ícones `lucide` e barra roxa no item ativo. Celular: barra inferior com ícone e rótulo (Hoje, Ciclo, Edital, Progresso, Config.; “Mais” quando entrarem Prática e Revisões). Ciclo mobile em lista; não esmagar 15 colunas. Suportar ampliação de texto a 200%.

## Fluxo A — Primeira utilização (09/10/2026)

`docker compose up -d` → abrir `http://127.0.0.1:8082` (ou a porta escolhida em `APP_PORT`) → app já tem catálogo, plano e template inicial (seed) → tela Hoje oferece **“Gerar semana”** (parcial: S13–S15) → **“Abrir o dia”** → missão com 3 blocos e check-out. Opcional: instalar como app no celular via endereço Tailscale. Sem formulário de cadastro.

## Fluxo B — Dia típico

```mermaid
flowchart TD
    OPEN["Hoje: Abrir o dia"] --> MISSION["Missão: blocos · revisões · questões · check-out"]
    MISSION --> BLOCK["Escolher bloco"]
    BLOCK --> FORM["Tópico efetivo, minutos, data (hoje por padrão)"]
    FORM --> VALID{"Válido?"}
    VALID -->|Não| FIX["Erro no campo; manter texto"] --> FORM
    VALID -->|Sim| SAVE["Salvar (UUID do cliente)"]
    SAVE --> NET{"Servidor confirmou?"}
    NET -->|Não| RETRY["Manter formulário; reenviar mesmo id"] --> SAVE
    NET -->|Sim| TOAST["Toast +XP; anel avança"]
    TOAST --> MORE{"Itens restantes?"}
    MORE -->|Sim| MISSION
    MORE -->|Não| DONE["Missão completa +50 XP; check-out"]
```

O formulário de sessão vem com o bloco, a data e o tópico sugerido preenchidos e “concluir bloco” marcado: o caminho feliz são 2 toques + minutos. Bloco indisponível → “Não se aplica hoje” ou “Remanejar”.

Sábado/domingo: “Abrir o dia” mostra a **missão livre**: escolher até 2 blocos pendentes da semana (remanejados para hoje), revisões pendentes e, opcionalmente, a meta de questões e o check-out. Estudo fora disso entra como sessão avulsa. Se não abrir, nada é cobrado.

## Fluxo C — Praticar questões (F2)

Resolver em plataforma externa → Prática → prova/tópico → fonte e contagens → validar total → salvar → nota líquida, taxa de acerto, amostra e `+XP` → registrar erro quando necessário.

Mensagem exemplo: “10 itens · 6 acertos · 4 erros · nota líquida 4/20 em P3. Lote parcial; não comparável ao mínimo oficial. +10 XP.”

## Fluxo D — Revisar (F3)

Missão ou fila → tarefa → nota/erro de origem → estudar fora → sessão de revisão opcional → concluir. Concluir não cria minutos. Atrasada continua visível sem duplicação.

## Fluxo E — Discursiva (F4)

Tipo → referência/enunciado → treinar → duração e linhas → rubrica → salvar → nota pessoal opcional. “30 linhas” é limite do edital; “nota pessoal” é avaliação, nunca oficial.

## Fluxo F — Chefão de etapa (F4)

Jornada → etapa atual → metas e chefão → criar simulado → associar lotes P1/P2/P3 até 40/40/90 → chefão derrotado (+100 XP), mínimos comparados → associar discursivas → NFC estimada só com duas notas manuais. Após o chefão da etapa 1, mostrar sugestão de rebalanceamento com aceitar/ajustar/recusar.

## Fluxo G — Remanejar, folga e restaurar

Remanejar: editar data/janela de ocorrência pendente → preview → salvar a mesma ocorrência. Folga: Configurações ou Hoje → “Marcar folga” (feriado/doença/compromisso) → sequência recalculada. Restaurar (F5): selecionar JSON → dry-run com novos/iguais/conflitantes → confirmar → transação única.

## Estados obrigatórios

| Situação | Comportamento |
|---|---|
| Sem registros | Ciclo e “Abrir o dia”; HUD em Nv 1 com 0 XP, sem números fictícios |
| Semana não gerada | Botão “Gerar semana”; consulta não grava |
| Dia não aberto | Botão “Abrir o dia” com prévia dos itens |
| Carregamento | Esqueleto discreto; não exibir zero como resultado |
| Rede indisponível | Manter formulário; explicar que salvar depende do servidor (Mac ligado) |
| Reenvio | Retornar registro original, sem duplicar |
| Edição concorrente | Avisar conflito, recarregar; não sobrescrever |
| Sequência em jogo | “Hoje ainda conta: faltam N min para manter a sequência” |
| Congelamento usado | Marcar o dia no histórico com ❄ |
| Nenhuma resposta válida | Taxa de acerto indisponível, não 0% |
| Exclusão de sessão | Confirmar efeito em métricas, revisões e XP |
| Fonte com retificação | Exibir versão do edital usada |

## Microtextos fixados

- “Abrir o dia”, “Registrar sessão”, “Remanejar bloco”, “Não se aplica hoje”, “Concluir revisão”.
- “XP mede constância, não preparo.”
- “Cobertura declarada não mede domínio do conteúdo.”
- “Resultado parcial: não é comparação com os mínimos da prova completa.”
- “Nota discursiva informada pelo usuário ou revisor; não é nota oficial.”
- “Os dados só serão salvos após confirmação do servidor.”
