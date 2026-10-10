# Visual BeroLab + Trophy UI — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar a identidade visual pela da BeroLab (grafite, roxo lavanda, dourado; Inter, Fira Mono, Departure Mono), adotar shadcn e os componentes do Trophy UI, e criar a tela Progresso (sequência com calendário, gráfico de XP e trilha de níveis), com diálogo de subida de nível.

**Architecture:** A paleta passa a viver nos tokens semânticos do shadcn (`--background`, `--card`, `--primary`…) em `src/index.css`, e as telas existentes trocam as classes antigas pelas novas. Os componentes do Trophy são copiados para `src/components/ui/` (código nosso, traduzido para pt-BR) e alimentados por **adaptadores puros** em `src/shared/game/adapters.ts`. A API ganha `GET /game/calendar`, os títulos de nível em `GET /game/config` e `level_title` no `game_delta`.

**Tech Stack:** shadcn CLI 4.21 (style `radix-nova`), Trophy UI (registry MIT), lucide-react, recharts, @radix-ui/react-tooltip, Tailwind 4.3, `@fontsource/inter`, `@fontsource/fira-mono`, Departure Mono 1.500 (MIT, auto-hospedada).

**Spec:** decisões do grilling de 10/10/2026, registradas nas rodadas 1 e 2 desta conversa e consolidadas em `docs/06-ux-e-fluxos.md` (Tarefa 7). Base: `docs/10-gamificacao-e-rotina.md`.

## Global Constraints

- Tema escuro único. Tokens: background `#161718`, card `#1b1c1d`, muted/secondary `#232525`, popover `#1b1c1d`, borda `rgb(255 255 255 / 0.10)`, input `rgb(255 255 255 / 0.16)`, foreground `#eeeeee`, muted-foreground `#919191`, primary `#b78cf2` com primary-foreground `#161718`, ring `#b78cf2`, xp `#f2c94f`, streak `#fb923c`, success `#22c55e`, destructive `#f87171`, info (congelamento) `#54a2ff`, P1 `#54a2ff`, P2 `#ffb96d`, P3 `#00d294`.
- Fontes: `--font-sans` Inter; `--font-mono` Fira Mono (números, códigos de tópico, rótulos em caixa alta com `tracking-widest`); `--font-pixel` Departure Mono (somente HUD: nível, XP, D-n, e a marca "CGU 2026").
- Todos os textos visíveis e `aria-label` em pt-BR. Sequência fala em **dias úteis**.
- Componentes do Trophy entram por `scripts/trophy_add.py` (a CLI do shadcn não resolve as dependências internas do Trophy) e são editados no próprio arquivo copiado.
- Não mudar regras de jogo nem contratos existentes; só **acrescentar** `GET /game/calendar`, `levels` em `/game/config` e `level_title` no `game_delta`.
- Sem conquistas (F5) e sem placares (usuário único).

## Review Focus

1. **Fim de semana e folga no calendário** devem aparecer neutros, nunca como falha (Tarefa 1 `test_calendar_marks_active_frozen_and_neutral_days`; Tarefa 3 teste do estado neutro).
2. **XP com lançamento datado no futuro** (semana completa cai no domingo) não pode inflar o gráfico até hoje (Tarefa 4 `toXpSeries ignora lançamentos fora do intervalo`).
3. **Contraste do botão roxo** com texto escuro, e foco visível em roxo (verificado nas capturas da Tarefa 7).
4. **Diálogo de nível** aparece uma única vez por subida e fecha com "Continuar" e com Esc (Tarefa 5).
5. **Intervalo inválido no calendário** (fim antes do início, mais de 400 dias) retorna 422 (Tarefa 1).

---

### Task 1: API — calendário da sequência, títulos de nível e `level_title`

**Files:**
- Modify: `apps/api/app/game/snapshot.py` (função `calendar`, campo `level_title`), `apps/api/app/game/router.py` (rota e `levels` no config)
- Test: `apps/api/tests/integration/test_game.py`

**Interfaces:**
- Produces: `GET /game/calendar?from=&to=` → `{active_days: [YYYY-MM-DD], frozen_days: [...], neutral_days: [...]}`; `GET /game/config` → acrescenta `levels: [{from, to, title}]`; `game_delta.level_title: str | null`.

- [ ] **Step 1: Testes que falham** — acrescentar em `test_game.py`:

```python
def test_calendar_marks_active_frozen_and_neutral_days(client, clock):
    clock.today = date(2026, 10, 21)
    study(client, date(2026, 10, 9), 45)
    for i in range(5):
        study(client, date(2026, 10, 12) + timedelta(days=i), 180)
    client.put("/api/v1/day-offs/2026-10-20", json={"reason": "consulta"})
    cal = client.get("/api/v1/game/calendar", params={"from": "2026-10-09", "to": "2026-10-21"}).json()
    assert cal["active_days"] == ["2026-10-09", "2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16"]
    assert cal["frozen_days"] == ["2026-10-19"]
    assert cal["neutral_days"] == ["2026-10-10", "2026-10-11", "2026-10-17", "2026-10-18", "2026-10-20"]


def test_calendar_rejects_invalid_range(client):
    assert client.get("/api/v1/game/calendar", params={"from": "2026-10-20", "to": "2026-10-09"}).status_code == 422
    assert client.get("/api/v1/game/calendar", params={"from": "2026-01-01", "to": "2027-03-01"}).status_code == 422


def test_config_exposes_level_titles(client):
    levels = client.get("/api/v1/game/config").json()["levels"]
    assert [l["title"] for l in levels] == ["Estagiário", "Analista", "Auditor Júnior", "Auditor", "AFFC"]
    assert levels[-1] == {"from": 18, "to": None, "title": "AFFC"}
```

E em `test_level_up_reported`, depois de `assert delta["level_up"] == 2`: `assert delta["level_title"] == "Estagiário"`.

- [ ] **Step 2: Ver falhar** — `docker compose --profile test run --rm test pytest tests/integration/test_game.py -q` → FAIL (404 em `/game/calendar`, `KeyError: 'levels'`, `KeyError: 'level_title'`).

- [ ] **Step 3: Implementar** — em `snapshot.py`, no dicionário de `game_delta`, acrescentar
`"level_title": after.level.title if after.level.level > before.level.level else None,` e a função:

```python
def calendar(db: Session, today: date, start: date, end: date) -> dict:
    """Dias ativos (≥ mínimo), congelados e neutros (fim de semana ou folga) no intervalo."""
    settings = db.get(AppSettings, 1)
    plan = current_plan(db)
    world = load_world(db)
    day_offs = set(db.scalars(select(DayOff.day)))
    streak = streak_state(world.minutes_by_date, day_offs, set(complete_weeks(db, world)), plan.starts_on, today,
                          settings.streak_min_minutes, settings.max_freezes)
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    active = [d for d in days if world.minutes_by_date.get(d, 0) >= settings.streak_min_minutes]
    neutral = [d for d in days if d not in active and (d.weekday() >= 5 or d in day_offs)]
    return {
        "active_days": active,
        "frozen_days": [d for d in streak.frozen_days if start <= d <= end],
        "neutral_days": neutral,
    }
```

Em `router.py`, a rota (antes de `/game/config`) e o campo `levels`:

```python
@router.get("/game/calendar")
def get_calendar(from_: date = Query(alias="from"), to: date = Query(), db: Session = Depends(get_db),
                 today: date = Depends(get_today)):
    if to < from_ or (to - from_).days > 400:
        raise ApiError(422, "invalid_range", "Intervalo inválido (máximo de 400 dias).")
    return snapshot.calendar(db, today, from_, to)
```

```python
    return {"holiday_suggestions": cfg.get("holiday_suggestions", []), "milestones": cfg["milestones"],
            "levels": cfg["levels"]["titles"]}
```

- [ ] **Step 4: Ver passar** — `docker compose --profile test run --rm test` → 80 passed.
- [ ] **Step 5: Commit** — `feat(api): calendário da sequência, títulos de nível e level_title`.

---

### Task 2: Base shadcn, tema BeroLab, fontes e migração de classes

**Files:**
- Modify: `apps/web/{tsconfig.json,tsconfig.app.json,vite.config.ts,package.json,index.html}`, `src/index.css`, `src/main.tsx`, todos os `.tsx` em `src/app` e `src/features`, `src/shared/ui/GameToast.tsx`
- Create: `apps/web/components.json`, `src/lib/utils.ts`, `src/components/ui/button.tsx` (gerados), `public/fonts/DepartureMono-Regular.woff2`, `public/fonts/DepartureMono-LICENSE.txt`

**Interfaces:**
- Produces: alias `@/` → `src/`; utilitário `cn` em `@/lib/utils`; classes semânticas `bg-background, bg-card, bg-muted, text-foreground, text-muted-foreground, border-border, bg-primary, text-primary-foreground, text-xp, text-streak, text-success, text-destructive, text-p1/p2/p3, font-sans, font-mono, font-pixel`.

- [ ] **Step 1: Alias** — em `tsconfig.json` e `tsconfig.app.json`, `compilerOptions.paths = {"@/*": ["./src/*"]}`; em `vite.config.ts`, `import path from 'node:path'` e `resolve: { alias: { '@': path.resolve(import.meta.dirname, './src') } }`.
- [ ] **Step 2: shadcn** — `cd apps/web && npx shadcn@latest init -t vite -b radix -p nova -y --no-monorepo < /dev/null` (stdin fechado evita prompt pendurado). Gera `components.json`, `src/lib/utils.ts`, `src/components/ui/button.tsx` e reescreve `src/index.css`.
- [ ] **Step 3: Fontes** — `npm install @fontsource/fira-mono && npm uninstall @fontsource/chakra-petch @fontsource/jetbrains-mono @fontsource-variable/geist`; baixar `https://github.com/rektdeckard/departure-mono/releases/download/v1.500/DepartureMono-1.500.zip` (SHA-256 `bf3e48059aeef4617ec585bdea81dcc3491c576b3e7a472f52faf40e09ee5c3a`) e copiar `DepartureMono-Regular.woff2` e `LICENSE` para `public/fonts/`. Em `main.tsx`, imports `@fontsource/inter/{400,500,600,700}.css` e `@fontsource/fira-mono/{400,500}.css`.
- [ ] **Step 4: Tema** — substituir `src/index.css` por:

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";

@font-face {
  font-family: "Departure Mono";
  src: url("/fonts/DepartureMono-Regular.woff2") format("woff2");
  font-display: swap;
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --color-chart-1: var(--chart-1);
  --color-chart-2: var(--chart-2);
  --color-chart-3: var(--chart-3);
  --color-chart-4: var(--chart-4);
  --color-chart-5: var(--chart-5);
  --color-info: var(--info);
  --color-info-foreground: var(--info-foreground);
  --color-xp: var(--xp);
  --color-streak: var(--streak);
  --color-success: var(--success);
  --color-p1: var(--p1);
  --color-p2: var(--p2);
  --color-p3: var(--p3);
  --font-sans: "Inter", system-ui, sans-serif;
  --font-mono: "Fira Mono", ui-monospace, monospace;
  --font-pixel: "Departure Mono", "Fira Mono", monospace;
  --radius-sm: calc(var(--radius) * 0.6);
  --radius-md: calc(var(--radius) * 0.8);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) * 1.4);
  --radius-2xl: calc(var(--radius) * 1.8);
}

:root {
  color-scheme: dark;
  --radius: 0.625rem;
  --background: #161718;
  --foreground: #eeeeee;
  --card: #1b1c1d;
  --card-foreground: #eeeeee;
  --popover: #1b1c1d;
  --popover-foreground: #eeeeee;
  --primary: #b78cf2;
  --primary-foreground: #161718;
  --secondary: #232525;
  --secondary-foreground: #eeeeee;
  --muted: #232525;
  --muted-foreground: #919191;
  --accent: #363737;
  --accent-foreground: #eeeeee;
  --destructive: #f87171;
  --border: rgb(255 255 255 / 0.1);
  --input: rgb(255 255 255 / 0.16);
  --ring: #b78cf2;
  --chart-1: #b78cf2;
  --chart-2: #f2c94f;
  --chart-3: #00d294;
  --chart-4: #54a2ff;
  --chart-5: #ffb96d;
  --info: #54a2ff;
  --info-foreground: #161718;
  --xp: #f2c94f;
  --streak: #fb923c;
  --success: #22c55e;
  --p1: #54a2ff;
  --p2: #ffb96d;
  --p3: #00d294;
}

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground font-sans antialiased;
    font-size: 16px;
  }
}

:focus-visible {
  outline: 2px solid var(--ring);
  outline-offset: 2px;
}

.num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important;
    transition: none !important;
  }
}
```

Em `index.html`, `theme-color` e o manifest passam a `#161718` (também `background_color`/`theme_color` em `public/manifest.webmanifest`).

- [ ] **Step 5: Migrar classes** — em `src/app`, `src/features` e `src/shared/ui`, aplicar exatamente:

| Antes | Depois |
|---|---|
| `bg-bg` | `bg-background` |
| `bg-surface-2` | `bg-muted` |
| `bg-surface` | `bg-card` |
| `text-text` | `text-foreground` |
| `text-muted` (sem sufixo) | `text-muted-foreground` |
| `hover:text-text` | `hover:text-foreground` |
| `bg-primary px-… text-white` / `text-white` em botão primário | `text-primary-foreground` |
| `text-danger` / `border-danger/50` | `text-destructive` / `border-destructive/50` |
| `border-xp/40` | `border-xp/40` (mantém) |
| `font-display` | `font-semibold` em títulos; `font-pixel` em `Hud.tsx` e na marca |
| `bg-bg/95` | `bg-background/95` |
| `var(--color-surface-2)` / `var(--color-xp)` / `var(--color-text)` (MissionRing) | `var(--muted)` / `var(--xp)` / `var(--foreground)` |

Verificação: `grep -rnE "bg-bg|bg-surface|text-text|text-white|text-danger|font-display|--color-(surface|text|xp)" src` → nenhuma linha; `grep -rn "text-muted\b[^-]" src` → nenhuma.

- [ ] **Step 6: Ver passar** — `npm test` (7 passed) e `npm run build` (`✓ built`).
- [ ] **Step 7: Commit** — `feat(web): shadcn, tema BeroLab e fontes Inter/Fira Mono/Departure Mono`.

---

### Task 3: Componentes do Trophy em pt-BR, com estado neutro no calendário

**Files:**
- Create: `scripts/trophy_add.py`; `src/components/ui/{points-badge,streak-card,streak-calendar,points-chart,points-levels-timeline,achievement-unlocked,achievement-badge}.tsx` (copiados e editados)
- Test: `src/components/ui/streak-calendar.test.tsx`

**Interfaces:**
- Produces: `StreakCalendar` aceita `neutralDates?: string[]` (YYYY-MM-DD); `StreakCard` aceita `neutralDates?: string[]` e repassa ao calendário; demais componentes com textos em pt-BR.

- [ ] **Step 1: Script e cópia**

```python
"""Copia componentes do registry Trophy (shadcn) resolvendo as dependências entre eles.

Uso: python3 scripts/trophy_add.py apps/web points-badge streak-card ...
Grava em <web>/src/components/ui/ e imprime as dependências npm e os itens shadcn a instalar.
"""

import json
import sys
import urllib.request
from pathlib import Path

BASE = "https://ui.trophy.so/r/{}.json"


def fetch(name: str) -> dict:
    with urllib.request.urlopen(BASE.format(name)) as response:
        return json.load(response)


def main() -> None:
    web = Path(sys.argv[1])
    catalog = {item["name"] for item in fetch("registry")["items"]}
    pending, seen, npm, shadcn = list(sys.argv[2:]), set(), set(), set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        item = fetch(name)
        npm.update(item.get("dependencies") or [])
        for dep in item.get("registryDependencies") or []:
            if dep in catalog:
                pending.append(dep)
            else:
                shadcn.add(dep)
        for file in item["files"]:
            out = web / "src/components/ui" / Path(file["path"]).name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(file["content"])
            print("escrito", out.relative_to(web))
    print("npm:", " ".join(sorted(npm)))
    print("shadcn:", " ".join(sorted(shadcn)))


if __name__ == "__main__":
    main()
```

```bash
python3 scripts/trophy_add.py apps/web points-badge streak-card points-chart points-levels-timeline achievement-unlocked
cd apps/web && npm install recharts @radix-ui/react-tooltip lucide-react class-variance-authority
```

Expected: 7 arquivos escritos; `shadcn: button` (já existe da Tarefa 2).

- [ ] **Step 2: Teste que falha** — `src/components/ui/streak-calendar.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StreakCalendar } from './streak-calendar'

describe('StreakCalendar', () => {
  it('mostra dias neutros, ativos e congelados em pt-BR', () => {
    render(
      <StreakCalendar view="month" month={new Date(2026, 9, 1)} startOfWeek={1}
        streak={[{ periodStart: '2026-10-09', periodEnd: '2026-10-09' },
                 { periodStart: '2026-10-19', periodEnd: '2026-10-19', usedFreeze: true }]}
        neutralDates={['2026-10-10']} />,
    )
    expect(screen.getByText('Seg')).toBeInTheDocument()
    expect(screen.getByRole('gridcell', { name: /10 de outubro.*folga ou fim de semana/ })).toBeInTheDocument()
    expect(screen.getByRole('gridcell', { name: /9 de outubro.*sequência ativa/ })).toBeInTheDocument()
    expect(screen.getByRole('gridcell', { name: /19 de outubro.*congelamento usado/ })).toBeInTheDocument()
  })
})
```

Run: `npm test -- streak-calendar` → FAIL (`Unable to find … Seg`).

- [ ] **Step 3: Editar os componentes copiados**

`streak-calendar.tsx`:
- `const WEEKDAYS_SUNDAY = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]` e `const WEEKDAYS_MONDAY = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]`.
- Trocar todas as ocorrências de `"en-US"` por `"pt-BR"`.
- Prop nova na interface: `/** Datas neutras (folga ou fim de semana), YYYY-MM-DD */ neutralDates?: string[]`; desestruturar `neutralDates = []` e criar `const neutralSet = new Set(neutralDates)`.
- `getCellState` passa a devolver também `isNeutral: !isActive && !usedFreeze && neutralSet.has(formatDateKey(date))`.
- Rótulos de status (visões mês e semana): `usedFreeze ? "congelamento usado" : isActive ? "sequência ativa" : isNeutral ? "folga ou fim de semana" : isFuture ? "futuro" : "sem atividade"`; `", today"` → `", hoje"`; `aria-label` do grid → `` `Calendário da sequência, visão ${view === "month" ? "mensal" : view === "week" ? "semanal" : "anual"}` ``.
- Classe adicional nas células (mês e semana): `isNeutral && "bg-muted/40 text-muted-foreground border-dashed"`.
- `freezeColorStyles` já usa `var(--info)` / `var(--info-foreground)` (definidos na Tarefa 2).

`streak-card.tsx`:
- Prop `neutralDates?: string[]` repassada a `<StreakCalendar … neutralDates={neutralDates} />`.
- Padrões: `title = "Sequência"`, `actionLabel = "Ver calendário"`, `howItWorksTitle = "Como funciona a sequência?"`, `howItWorksItems = ["Um dia útil conta quando você estuda ao menos 30 minutos.", "Fim de semana e folgas declaradas não quebram nem somam.", "Cada semana completa rende 1 congelamento (máx. 2), que cobre um dia útil perdido."]`.
- `days` → `dias úteis`; `Longest Streak` → `Recorde`; `Total` → `Congelamentos`; `aria-label="Streak summary card"` → `"Resumo da sequência"`; `"Streak stats"` → `"Números da sequência"`.
- Remover o import não usado `ChevronRight` (quebra o `tsc` com `noUnusedLocals`).

`achievement-unlocked.tsx`:
- `"Share"` → `"Compartilhar"`; `"Earned today"` → `"Conquistado hoje"`; `` `Earned ${date.toLocaleDateString(undefined, …)}` `` → `` `Conquistado em ${date.toLocaleDateString("pt-BR", …)}` ``; `aria-label="Close"` → `"Fechar"`; `Awesome!` → `Continuar`; backdrop `bg-foreground/80` → `bg-black/70` (no tema escuro `foreground` é claro).

`achievement-badge.tsx`: `"Earned"` → `"Conquistado"`, `"Locked"` → `"Bloqueado"`, `` `${achievement.name} badge - ${statusLabel}` `` → `` `Emblema ${achievement.name} - ${statusLabel}` ``.

`points-chart.tsx`: `title = "Your points"` → `title = "XP acumulado"`; `.toLocaleString()` → `.toLocaleString("pt-BR")`.

`points-levels-timeline.tsx`: `currentLevelLabel = "Current"` → `"Atual"`; `aria-label="Points levels"` → `"Níveis de XP"`; `.toLocaleString()` → `.toLocaleString("pt-BR")`.

`points-badge.tsx`: `total.toLocaleString()` → `total.toLocaleString("pt-BR")`.

Verificação: `grep -nE '"(en-US|Share|Close|Awesome|Earned|Locked|Current|Your points|Streak|Longest)' src/components/ui/*.tsx` → nenhuma linha.

- [ ] **Step 4: Ver passar** — `npm test` (8 passed), `npm run build`.
- [ ] **Step 5: Commit** — `feat(web): componentes Trophy em pt-BR com estado neutro no calendário`.

---

### Task 4: Adaptadores puros (API → props do Trophy)

**Files:**
- Create: `src/shared/game/adapters.ts`
- Test: `src/shared/game/adapters.test.ts`

**Interfaces:**
- Consumes: `addDays` de `@/shared/format`.
- Produces: `toStreakPeriods(cal: CalendarDays): StreakPeriod[]`, `cumulativeXp(level: number): number`, `toXpSeries(entries: XpEntry[], from: string, to: string): XpPoint[]`, `levelLines(level: number): {value: number; color: string}[]`, `toLevelsTimeline(bands: TitleBand[]): LevelTimelineItem[]`; tipos `CalendarDays, StreakPeriod, XpEntry, XpPoint, TitleBand, LevelTimelineItem`.

- [ ] **Step 1: Testes que falham** — `src/shared/game/adapters.test.ts`:

```ts
import { describe, expect, it } from 'vitest'

import { cumulativeXp, levelLines, toLevelsTimeline, toStreakPeriods, toXpSeries } from './adapters'

describe('adaptadores do jogo', () => {
  it('converte dias ativos e congelados em períodos de um dia, ordenados', () => {
    expect(toStreakPeriods({ active_days: ['2026-10-12', '2026-10-09'], frozen_days: ['2026-10-19'], neutral_days: ['2026-10-10'] }))
      .toEqual([
        { periodStart: '2026-10-09', periodEnd: '2026-10-09' },
        { periodStart: '2026-10-12', periodEnd: '2026-10-12' },
        { periodStart: '2026-10-19', periodEnd: '2026-10-19', usedFreeze: true },
      ])
  })

  it('acumula XP por dia, preenchendo dias sem registro', () => {
    const entries = [{ date: '2026-10-09', xp: 75 }, { date: '2026-10-09', xp: 50 }, { date: '2026-10-12', xp: 30 }]
    expect(toXpSeries(entries, '2026-10-09', '2026-10-12')).toEqual([
      { date: '2026-10-09', total: 125, change: 125 },
      { date: '2026-10-10', total: 125, change: 0 },
      { date: '2026-10-11', total: 125, change: 0 },
      { date: '2026-10-12', total: 155, change: 30 },
    ])
  })

  it('toXpSeries ignora lançamentos fora do intervalo', () => {
    const entries = [{ date: '2026-10-09', xp: 10 }, { date: '2026-10-18', xp: 150 }]
    expect(toXpSeries(entries, '2026-10-09', '2026-10-10').map((p) => p.total)).toEqual([10, 10])
  })

  it('calcula limiares de nível iguais aos do backend', () => {
    expect([cumulativeXp(1), cumulativeXp(4), cumulativeXp(18)]).toEqual([0, 600, 15300])
    expect(levelLines(4).map((l) => l.value)).toEqual([600, 1000])
  })

  it('monta a trilha de níveis a partir das faixas de título', () => {
    const items = toLevelsTimeline([
      { from: 1, to: 3, title: 'Estagiário' },
      { from: 18, to: null, title: 'AFFC' },
    ])
    expect(items).toEqual([
      { id: 'nv-1', name: 'Estagiário', description: 'Níveis 1–3', points: 0 },
      { id: 'nv-18', name: 'AFFC', description: 'Nível 18 em diante', points: 15300 },
    ])
  })
})
```

Run: `npm test -- adapters` → FAIL (`Failed to resolve import "./adapters"`).

- [ ] **Step 2: Implementar** — `src/shared/game/adapters.ts`:

```ts
import { addDays } from '@/shared/format'

export interface CalendarDays { active_days: string[]; frozen_days: string[]; neutral_days: string[] }
export interface StreakPeriod { periodStart: string; periodEnd: string; usedFreeze?: boolean }
export interface XpEntry { date: string; xp: number }
export interface XpPoint { date: string; total: number; change: number }
export interface TitleBand { from: number; to: number | null; title: string }
export interface LevelTimelineItem { id: string; name: string; description: string; points: number }

export function toStreakPeriods(cal: CalendarDays): StreakPeriod[] {
  const periods: StreakPeriod[] = [
    ...cal.active_days.map((d) => ({ periodStart: d, periodEnd: d })),
    ...cal.frozen_days.map((d) => ({ periodStart: d, periodEnd: d, usedFreeze: true })),
  ]
  return periods.sort((a, b) => a.periodStart.localeCompare(b.periodStart))
}

/** XP acumulado para estar no nível (mesma fórmula de docs/10 §4). */
export function cumulativeXp(level: number): number {
  return 50 * level * (level - 1)
}

export function toXpSeries(entries: XpEntry[], from: string, to: string): XpPoint[] {
  const byDay = new Map<string, number>()
  for (const e of entries) byDay.set(e.date, (byDay.get(e.date) ?? 0) + e.xp)
  const series: XpPoint[] = []
  let total = 0
  for (let day = from; day <= to; day = addDays(day, 1)) {
    const change = byDay.get(day) ?? 0
    total += change
    series.push({ date: day, total, change })
  }
  return series
}

export function levelLines(level: number): { value: number; color: string }[] {
  return [
    { value: cumulativeXp(level), color: 'var(--muted-foreground)' },
    { value: cumulativeXp(level + 1), color: 'var(--xp)' },
  ]
}

export function toLevelsTimeline(bands: TitleBand[]): LevelTimelineItem[] {
  return bands.map((b) => ({
    id: `nv-${b.from}`,
    name: b.title,
    description: b.to === null ? `Nível ${b.from} em diante` : `Níveis ${b.from}–${b.to}`,
    points: cumulativeXp(b.from),
  }))
}
```

- [ ] **Step 3: Ver passar** — `npm test` (13 passed).
- [ ] **Step 4: Commit** — `feat(web): adaptadores do jogo para os componentes Trophy`.

---

### Task 5: Navegação com ícones, HUD com `points-badge` e diálogo de nível

**Files:**
- Modify: `src/app/App.tsx`, `src/app/Hud.tsx`, `src/shared/ui/GameToast.tsx`, `src/shared/api/types.ts` (`GameDelta.level_title`)
- Test: `src/shared/ui/GameToast.test.tsx`

**Interfaces:**
- Consumes: `AchievementUnlocked` (Tarefa 3).
- Produces: `GameToastProvider` abre o diálogo quando `delta.level_up` vem preenchido; rota `/progresso` no menu (página na Tarefa 6).

- [ ] **Step 1: Teste que falha** — `src/shared/ui/GameToast.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { GameDelta } from '../api/types'
import { GameToastProvider, useGameToast } from './GameToast'

function Trigger({ delta }: { delta: GameDelta }) {
  const show = useGameToast()
  return <button onClick={() => show(delta)}>disparar</button>
}

const levelUp: GameDelta = {
  xp_gained: 120, entries: [{ source: 'session_minutes', ref_id: 's', date: '2026-10-12', xp: 120 }],
  level_up: 2, level_title: 'Estagiário', mission_complete: [], streak: 2,
}

describe('diálogo de subida de nível', () => {
  it('abre com nível e título e fecha em Continuar', async () => {
    render(<GameToastProvider><Trigger delta={levelUp} /></GameToastProvider>)
    const user = userEvent.setup()
    await user.click(screen.getByText('disparar'))
    expect(screen.getByRole('dialog')).toHaveTextContent('Nível 2 · Estagiário')
    expect(screen.getByRole('dialog')).toHaveTextContent('XP mede constância, não preparo.')
    await user.click(screen.getByRole('button', { name: 'Continuar' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('fecha com Esc', async () => {
    render(<GameToastProvider><Trigger delta={levelUp} /></GameToastProvider>)
    const user = userEvent.setup()
    await user.click(screen.getByText('disparar'))
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('não abre sem subida de nível', async () => {
    render(<GameToastProvider><Trigger delta={{ ...levelUp, level_up: null, level_title: null }} /></GameToastProvider>)
    await userEvent.setup().click(screen.getByText('disparar'))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
```

Run: `npm test -- GameToast` → FAIL (nenhum `dialog`).

- [ ] **Step 2: Implementar**
- `types.ts`: em `GameDelta`, `level_title: string | null`.
- `GameToast.tsx`: estado `const [levelUp, setLevelUp] = useState<{ level: number; title: string } | null>(null)`; em `show`, `if (delta.level_up) setLevelUp({ level: delta.level_up, title: delta.level_title ?? '' })` e o toast deixa de mostrar a linha "Nível X!"; renderizar:

```tsx
{levelUp && (
  <AchievementUnlocked
    open
    onOpenChange={(open) => { if (!open) setLevelUp(null) }}
    achievement={{
      id: `nv-${levelUp.level}`,
      name: `Nível ${levelUp.level} · ${levelUp.title}`,
      description: 'XP mede constância, não preparo.',
      trigger: 'metric',
    }}
  />
)}
```

- `App.tsx`: `LINKS` com ícones lucide — `{ to: '/', label: 'Hoje', icon: House }`, `{ to: '/ciclo', label: 'Ciclo', icon: CalendarDays }`, `{ to: '/edital', label: 'Edital', icon: BookOpen }`, `{ to: '/progresso', label: 'Progresso', icon: Trophy }`, `{ to: '/config', label: 'Config.', icon: Settings }`; cada `NavLink` renderiza `<l.icon className="size-5" aria-hidden="true" />` e o rótulo (no celular, ícone acima do rótulo em `text-xs`); item ativo: `text-primary` e, no desktop, `md:border-r-2 md:border-primary`; marca `CGU 2026` em `font-pixel text-xl text-primary`.
- `Hud.tsx`: nível e título em `font-pixel`; XP total com `<PointsBadge name="XP" total={data.xp_total} size="sm" />`; barra do nível em `bg-xp`; `🔥` vira `<Flame className="size-4 text-streak" aria-hidden="true" />`, `❄` vira `<Snowflake className="size-4 text-info" aria-hidden="true" />`; `D-{n}` em `font-pixel text-xp`.

- [ ] **Step 3: Ver passar** — `npm test` (16 passed), `npm run build`.
- [ ] **Step 4: Commit** — `feat(web): navegação com ícones, XP no HUD e diálogo de subida de nível`.

---

### Task 6: Tela Progresso

**Files:**
- Create: `src/features/progress/ProgressPage.tsx`
- Modify: `src/app/App.tsx` (rota `/progresso`), `src/shared/api/hooks.ts` (`useCalendar`, `useXpLedger`, `useGameConfig`), `src/shared/api/types.ts` (`GameConfig`)

**Interfaces:**
- Consumes: `GET /game/calendar`, `GET /game/xp`, `GET /game/config`, `GET /game/summary`; adaptadores da Tarefa 4; `StreakCard`, `StreakCalendar`, `PointsChart`, `PointsLevelsTimeline`.

- [ ] **Step 1: Hooks** (em `hooks.ts`):

```ts
export const useCalendar = (from: string, to: string) =>
  useQuery({ queryKey: ['calendar', from, to], queryFn: () => api<CalendarDays>(`/game/calendar?from=${from}&to=${to}`) })

export const useXpLedger = (from: string, to: string) =>
  useQuery({ queryKey: ['xp', from, to], queryFn: () => api<ListResponse<XpEntry>>(`/game/xp?from=${from}&to=${to}`) })

export const useGameConfig = () =>
  useQuery({ queryKey: ['game-config'], queryFn: () => api<GameConfig>('/game/config'), staleTime: Infinity })
```

`types.ts`: `export interface GameConfig { levels: TitleBand[]; holiday_suggestions: { date: string; label: string }[] }` (importando `TitleBand` de `@/shared/game/adapters`). Acrescentar `'calendar'` e `'xp'` à lista invalidada em `useGameMutation`.

- [ ] **Step 2: Página** — `ProgressPage.tsx`:

```tsx
import { PointsChart } from '@/components/ui/points-chart'
import { PointsLevelsTimeline } from '@/components/ui/points-levels-timeline'
import { StreakCalendar } from '@/components/ui/streak-calendar'
import { StreakCard } from '@/components/ui/streak-card'
import { useCalendar, useGameConfig, useSummary, useXpLedger } from '@/shared/api/hooks'
import { levelLines, toLevelsTimeline, toStreakPeriods, toXpSeries } from '@/shared/game/adapters'

const PLAN_START = '2026-10-09'

export function ProgressPage() {
  const summary = useSummary()
  const today = summary.data?.today ?? PLAN_START
  const calendar = useCalendar(PLAN_START, today)
  const ledger = useXpLedger(PLAN_START, today)
  const config = useGameConfig()
  if (!summary.data || !calendar.data || !ledger.data || !config.data) {
    return <p className="text-muted-foreground" aria-busy="true">Carregando…</p>
  }
  const s = summary.data
  const periods = toStreakPeriods(calendar.data)
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Progresso</h1>
      <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
        XP mede constância, não preparo
      </p>
      <StreakCard streak={periods} neutralDates={calendar.data.neutral_days}
        currentStreak={s.streak.current} longestStreak={s.streak.best} total={s.streak.freezes_available}
        actionLabel="" showHowItWorks />
      <section className="rounded-2xl border bg-card p-6">
        <StreakCalendar view="month" month={new Date(`${today}T12:00:00`)} startOfWeek={1}
          streak={periods} neutralDates={calendar.data.neutral_days} className="mx-auto" />
      </section>
      <PointsChart data={toXpSeries(ledger.data.items, PLAN_START, today)} levels={levelLines(s.level)}
        yAxisLabel="XP" title="XP acumulado" />
      <section className="rounded-2xl border bg-card p-6">
        <h2 className="mb-4 font-semibold">Níveis</h2>
        <PointsLevelsTimeline levels={toLevelsTimeline(config.data.levels)} currentPoints={s.xp_total}
          formatPoints={(v) => `${v.toLocaleString('pt-BR')}`} />
      </section>
    </div>
  )
}
```

Rota em `App.tsx`: `<Route path="/progresso" element={<ProgressPage />} />`.

- [ ] **Step 3: Ver passar** — `npm test` (16 passed), `npm run build`.
- [ ] **Step 4: Commit** — `feat(web): tela Progresso com sequência, calendário, XP e níveis`.

---

### Task 7: Documentação e validação visual

**Files:**
- Modify: `docs/06-ux-e-fluxos.md` (tokens, fontes, navegação, tela Progresso, componentes Trophy), `README.md` (changelog 2.1)

- [ ] **Step 1:** Atualizar `docs/06` com a tabela de tokens da Tarefa 2, as três famílias de fonte, a navegação com ícones e a tela Progresso; registrar no changelog do README a versão 2.1 (visual BeroLab + Trophy UI).
- [ ] **Step 2:** `docker compose up -d --build app`; gerar capturas (360 px via iframe e 1280 px) de Hoje, Ciclo, Edital, Progresso e do diálogo de nível; conferir contraste do botão roxo (`#161718` sobre `#b78cf2` ≥ 4,5:1) e foco visível.
- [ ] **Step 3:** Rodar `docker compose --profile test run --rm test` (80 passed) e `cd apps/web && npm test` (16 passed).
- [ ] **Step 4: Commit** — `docs: visual BeroLab e Trophy UI (v2.1)`. Apresentar as capturas para aprovação antes do merge.
