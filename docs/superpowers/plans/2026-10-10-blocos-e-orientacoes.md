# Blocos remanejados e orientações por bloco — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar acessíveis os blocos que entram no dia depois de a missão ser aberta (e os atrasados), e dar a cada bloco do ciclo um roteiro de uso dos 60 min, com tópico, subitens, materiais e, nas discursivas, tema/caso no formato Cebraspe com espelho.

**Architecture:** Parte A é só frontend sobre contratos existentes (`GET /days`, `GET /occurrences`, `PATCH /occurrences/{id}`) mais `GET /plans/current`. Parte B adiciona um arquivo de conteúdo versionado (`docs/data/orientacoes.json`), funções puras de rodízio de temas em `app/domain/guidance.py`, um módulo `app/guidance/` (conteúdo, serviço e rota `GET /occurrences/{id}/guidance`), a coluna `occurrences.theme_id` (tema escolhido ou fixado pela primeira sessão) e o campo `theme_id` no `PATCH /occurrences/{id}`. No web, um painel `GuidancePanel` aparece nas linhas de bloco da tela Hoje e da tela Ciclo.

**Tech Stack:** FastAPI + SQLAlchemy 2 + Alembic + Postgres 17 (pytest; integração via `docker compose --profile test`), React 19 + TanStack Query 5 + Tailwind 4 (vitest + Testing Library).

**Spec:** [`docs/superpowers/specs/2026-10-10-blocos-e-orientacoes.md`](../specs/2026-10-10-blocos-e-orientacoes.md)

## Global Constraints

- Todos os textos visíveis e `aria-label` em pt-BR.
- Não mudar regras de XP, sequência nem de conclusão de missão. A missão continua uma foto fixa (`open_day` não muda).
- `GET` nunca grava (`test_get_day_does_not_write` continua valendo; o mesmo vale para `GET /occurrences/{id}/guidance`).
- Conteúdo só em `docs/data/orientacoes.json`; links só `https://` de fontes oficiais ou da banca.
- Formato das discursivas (edital 9.1/9.7): Q1 complementares até 30 linhas/30 pontos; Q2 situação-problema até 60 linhas/70 pontos; NQ1 = NC − 6 × NE ÷ TL; NQ2 = NC − 14 × NE ÷ TL; NFPD ≥ 50.
- "Semelhante à prova X" só com URL da fonte real. Nunca inventar "caiu em prova".
- S15 reduzido até **2026-11-22** (15 min esquema + 40 min escrevendo 2 aspectos + 5 min revisão).
- Novo título de S13: **"Complementares + revisão da semana"**.
- Todos os blocos do ciclo têm 60 min (02 §3): os passos de cada roteiro somam 60.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Bloco que saiu e voltou para o dia com a missão aberta** é item da missão: deve aparecer só na missão, nunca duplicado em "Outros blocos" (Tarefa 5, teste "não repete bloco da missão").
2. **Tema trocado depois de haver sessão** precisa ser recusado (`theme_locked`), e o tema exibido não pode mudar depois que a sessão é salva (Tarefa 4, `test_theme_is_fixed_after_session`).
3. **Conteúdo ausente** (tópico sem subitens/materiais, lista de temas vazia antes da Tarefa 9) não pode quebrar o painel: seções somem, tema vem `null` (Tarefa 4 `test_guidance_without_themes`; Tarefa 7 teste "omite seções vazias").
4. **Último dia do plano**: "Mover para amanhã" não aparece (Tarefa 5, teste "some no último dia do plano").
5. **Atrasados no primeiro dia do plano e blocos dispensados**: sem consulta quando ontem é anterior ao início do plano; dispensados não contam (Tarefa 6).

---

### Task 1: Domínio — roteiro vigente e rodízio de temas

**Files:**
- Create: `apps/api/app/domain/guidance.py`
- Test: `apps/api/tests/unit/test_guidance.py`

**Interfaces:**
- Produces:
  - `ThemeRef(occurrence_id: str, week_index: int, stored_theme_id: str | None, has_session: bool)` (dataclass frozen)
  - `resolve_themes(theme_ids: list[str], refs: list[ThemeRef]) -> dict[str, str | None]`
  - `next_theme(theme_ids: list[str], current: str, done: set[str]) -> str | None`
  - `pick_variant(variants: list[dict], day: date) -> dict` (variante = `{"ate": "YYYY-MM-DD" | None, "titulo": str, "passos": [...]}`)

- [ ] **Step 1: Testes que falham** — criar `apps/api/tests/unit/test_guidance.py`:

```python
from datetime import date

from app.domain.guidance import ThemeRef, next_theme, pick_variant, resolve_themes

IDS = ["D1", "D2", "D3"]


def ref(occ, week, stored=None, session=False):
    return ThemeRef(occ, week, stored, session)


def test_each_week_gets_its_theme_in_rotation():
    got = resolve_themes(IDS, [ref("a", 0), ref("b", 1), ref("c", 2), ref("d", 3)])
    assert got == {"a": "D1", "b": "D2", "c": "D3", "d": "D1"}


def test_stored_theme_wins():
    assert resolve_themes(IDS, [ref("a", 0, stored="D3")]) == {"a": "D3"}


def test_theme_done_in_earlier_week_is_skipped():
    got = resolve_themes(IDS, [ref("a", 0, stored="D2", session=True), ref("b", 1)])
    assert got == {"a": "D2", "b": "D3"}


def test_theme_without_session_is_not_done():
    got = resolve_themes(IDS, [ref("a", 0, stored="D2"), ref("b", 1)])
    assert got == {"a": "D2", "b": "D2"}


def test_removed_stored_theme_falls_back_to_rotation():
    assert resolve_themes(IDS, [ref("a", 1, stored="X9")]) == {"a": "D2"}


def test_no_themes_resolves_to_none():
    assert resolve_themes([], [ref("a", 0)]) == {"a": None}


def test_all_done_repeats_week_theme():
    refs = [ref("a", 0, session=True), ref("b", 1, session=True), ref("c", 2, session=True), ref("d", 3)]
    assert resolve_themes(IDS, refs)["d"] == "D1"


def test_next_theme_skips_done_and_wraps():
    assert next_theme(IDS, "D1", {"D2"}) == "D3"
    assert next_theme(IDS, "D3", set()) == "D1"
    assert next_theme(IDS, "D1", {"D2", "D3"}) is None
    assert next_theme(["D1"], "D1", set()) is None


def test_pick_variant_by_date():
    variants = [{"ate": "2026-11-22", "titulo": "Reduzido", "passos": []},
                {"ate": None, "titulo": "Completo", "passos": []}]
    assert pick_variant(variants, date(2026, 11, 22))["titulo"] == "Reduzido"
    assert pick_variant(variants, date(2026, 11, 23))["titulo"] == "Completo"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd apps/api && uv run pytest tests/unit/test_guidance.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.domain.guidance'`

- [ ] **Step 3: Implementar** — criar `apps/api/app/domain/guidance.py`:

```python
"""Orientação por bloco: variante de roteiro vigente e rodízio de temas discursivos (B5, B6). Funções puras."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ThemeRef:
    occurrence_id: str
    week_index: int
    stored_theme_id: str | None
    has_session: bool


def _first_free(theme_ids: list[str], start: int, done: set[str]) -> str:
    n = len(theme_ids)
    for k in range(n):
        candidate = theme_ids[(start + k) % n]
        if candidate not in done:
            return candidate
    return theme_ids[start % n]


def resolve_themes(theme_ids: list[str], refs: list[ThemeRef]) -> dict[str, str | None]:
    """Tema de cada ocorrência, em ordem de semana: o tema salvo vence; os demais pegam o tema
    da semana no rodízio, pulando os já feitos (com sessão) em semanas anteriores."""
    if not theme_ids:
        return {r.occurrence_id: None for r in refs}
    done: set[str] = set()
    result: dict[str, str | None] = {}
    for r in sorted(refs, key=lambda r: (r.week_index, r.occurrence_id)):
        if r.stored_theme_id in theme_ids:
            theme = r.stored_theme_id
        else:
            theme = _first_free(theme_ids, r.week_index % len(theme_ids), done)
        result[r.occurrence_id] = theme
        if r.has_session:
            done.add(theme)
    return result


def next_theme(theme_ids: list[str], current: str, done: set[str]) -> str | None:
    """Próximo tema depois de `current` que ainda não foi feito; None se não houver."""
    if current not in theme_ids:
        return None
    n = len(theme_ids)
    start = theme_ids.index(current)
    for k in range(1, n):
        candidate = theme_ids[(start + k) % n]
        if candidate not in done:
            return candidate
    return None


def pick_variant(variants: list[dict], day: date) -> dict:
    """Primeira variante cujo `ate` (inclusivo) não passou; a última tem `ate` nulo."""
    for v in variants:
        if v["ate"] is None or day <= date.fromisoformat(v["ate"]):
            return v
    return variants[-1]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd apps/api && uv run pytest tests/unit/test_guidance.py -q`
Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/domain/guidance.py apps/api/tests/unit/test_guidance.py
git commit -m "feat(api): rodízio de temas e roteiro vigente por data

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Conteúdo — `orientacoes.json` inicial e validador

**Files:**
- Create: `docs/data/orientacoes.json`, `apps/api/app/guidance/__init__.py` (vazio), `apps/api/app/guidance/content.py`
- Test: `apps/api/tests/unit/test_guidance_content.py`

**Interfaces:**
- Produces:
  - `content.guidance() -> dict` (lido de `config.DATA_DIR / "orientacoes.json"`, em cache; os testes de integração fazem `monkeypatch.setattr(content, "guidance", ...)`, então o serviço deve sempre chamar `content.guidance()` pelo módulo)
  - `content.validate(data: dict, topic_ids: set[str]) -> list[str]` (lista de problemas; vazia = válido)
  - Chaves do JSON: `roteiros_por_atividade` (`theory`, `questions`, `essay`), `roteiros_por_bloco` (`S13`, `S14`, `S15`), `primeira_semana` (código → texto), `subitens` (tópico → [str]), `materiais` (tópico → [{titulo, url, nota}]), `lembretes` (`complementary`, `technical_case` → [str]), `temas` (`complementary`, `technical_case` → [Tema]).
  - Tema: `{id, titulo, topic_ids, linhas, texto_motivador, comando, aspectos: [{texto, valor}], espelho: {texto_padrao, quesitos: [{id, texto, conceitos: [str]}]}, fontes: [{titulo, url}], semelhante_a: {prova, url} | null}`

- [ ] **Step 1: Testes que falham** — criar `apps/api/tests/unit/test_guidance_content.py`:

```python
import copy
import json

from app import config
from app.guidance import content


def catalog_topic_ids() -> set[str]:
    catalog = json.loads((config.DATA_DIR / "catalogo-edital.json").read_text(encoding="utf-8"))
    return {t["id"] for s in catalog["subjects"] for t in s["topics"]}


def theme(id, kind="complementary"):
    lines, points = (30, 30) if kind == "complementary" else (60, 70)
    return {"id": id, "titulo": "T", "topic_ids": ["C04.01"], "linhas": lines, "texto_motivador": "x",
            "comando": "Redija.", "aspectos": [{"texto": "a", "valor": points}],
            "espelho": {"texto_padrao": "p", "quesitos": [{"id": "2.1", "texto": "q", "conceitos": ["0", "1"]}]},
            "fontes": [{"titulo": "Edital", "url": "https://www.in.gov.br/"}], "semelhante_a": None}


def test_real_file_is_valid():
    assert content.validate(content.guidance(), catalog_topic_ids()) == []


def test_validator_catches_wrong_minutes_and_points():
    data = copy.deepcopy(content.guidance())
    data["roteiros_por_atividade"]["theory"][0]["passos"][0]["minutos"] += 1
    bad = theme("D1")
    bad["aspectos"][0]["valor"] = 25
    data["temas"]["complementary"] = [bad, theme("D1")]
    problems = content.validate(data, catalog_topic_ids())
    assert any("theory" in p and "61" in p for p in problems)
    assert any("D1" in p and "30" in p for p in problems)
    assert any("duplicado" in p for p in problems)


def test_validator_catches_unknown_topic_and_bad_url():
    data = copy.deepcopy(content.guidance())
    data["materiais"]["Z99.99"] = [{"titulo": "x", "url": "http://exemplo", "nota": ""}]
    problems = content.validate(data, catalog_topic_ids())
    assert any("Z99.99" in p for p in problems)
    assert any("https" in p for p in problems)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd apps/api && uv run pytest tests/unit/test_guidance_content.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.guidance'`

- [ ] **Step 3: Implementar o validador** — criar `apps/api/app/guidance/__init__.py` vazio e `apps/api/app/guidance/content.py`:

```python
"""Conteúdo de orientação por bloco (docs/data/orientacoes.json) e sua validação."""

import json
from functools import lru_cache

from app import config

ACTIVITIES = ("theory", "questions", "essay")
BLOCK_MINUTES = 60  # todos os blocos do ciclo têm 60 min (02 §3)
ESSAY_FORMAT = {"complementary": (30, 30), "technical_case": (60, 70)}  # linhas, pontos (edital 9.1)


@lru_cache
def guidance() -> dict:
    return json.loads((config.DATA_DIR / "orientacoes.json").read_text(encoding="utf-8"))


def _check_variants(name: str, variants: list[dict], problems: list[str]) -> None:
    if not variants:
        problems.append(f"{name}: sem roteiro")
        return
    if variants[-1]["ate"] is not None:
        problems.append(f"{name}: a última variante precisa ter ate = null")
    for v in variants:
        total = sum(p["minutos"] for p in v["passos"])
        if total != BLOCK_MINUTES:
            problems.append(f"{name}: passos somam {total} min, esperado {BLOCK_MINUTES}")


def _check_url(where: str, url: str, problems: list[str]) -> None:
    if not url.startswith("https://"):
        problems.append(f"{where}: link precisa ser https ({url})")


def validate(data: dict, topic_ids: set[str]) -> list[str]:
    problems: list[str] = []
    for activity in ACTIVITIES:
        _check_variants(activity, data["roteiros_por_atividade"].get(activity, []), problems)
    for code, variants in data["roteiros_por_bloco"].items():
        _check_variants(code, variants, problems)
    for key in ("subitens", "materiais"):
        for topic in data[key]:
            if topic not in topic_ids:
                problems.append(f"{key}: tópico inexistente {topic}")
    for topic, items in data["materiais"].items():
        if not 1 <= len(items) <= 3:
            problems.append(f"materiais {topic}: use de 1 a 3 materiais")
        for m in items:
            _check_url(f"materiais {topic}", m["url"], problems)
    seen: set[str] = set()
    for kind, (lines, points) in ESSAY_FORMAT.items():
        if not data["lembretes"].get(kind):
            problems.append(f"lembretes: faltam os de {kind}")
        for t in data["temas"][kind]:
            tid = t["id"]
            if tid in seen:
                problems.append(f"tema {tid}: id duplicado")
            seen.add(tid)
            if t["linhas"] != lines:
                problems.append(f"tema {tid}: {t['linhas']} linhas, esperado {lines}")
            total = round(sum(a["valor"] for a in t["aspectos"]), 2)
            if total != points:
                problems.append(f"tema {tid}: aspectos somam {total}, esperado {points}")
            if len(t["espelho"]["quesitos"]) != len(t["aspectos"]):
                problems.append(f"tema {tid}: um quesito por aspecto")
            if not t["fontes"]:
                problems.append(f"tema {tid}: sem fonte")
            for f in t["fontes"]:
                _check_url(f"tema {tid}", f["url"], problems)
            for topic in t["topic_ids"]:
                if topic not in topic_ids:
                    problems.append(f"tema {tid}: tópico inexistente {topic}")
            similar = t.get("semelhante_a")
            if similar is not None:
                _check_url(f"tema {tid} semelhante_a", similar.get("url", ""), problems)
    return problems
```

- [ ] **Step 4: Criar `docs/data/orientacoes.json`** com os roteiros e lembretes reais; `subitens`, `materiais` e `temas` começam vazios (Tarefas 8 e 9 preenchem):

```json
{
  "schema_version": 1,
  "exam_version_id": "edital-2026-10-08-v1",
  "roteiros_por_atividade": {
    "theory": [
      {"ate": null, "titulo": "Teoria em 60 min", "passos": [
        {"minutos": 5, "texto": "Leia os subitens do edital abaixo e escolha o recorte de hoje."},
        {"minutos": 30, "texto": "Leitura dirigida no material indicado, anotando conceitos e exceções."},
        {"minutos": 15, "texto": "Questões do tópico para testar o que acabou de ler."},
        {"minutos": 10, "texto": "Anote erros e pontos fracos: é isso que volta na revisão de sexta."}
      ]}
    ],
    "questions": [
      {"ate": null, "titulo": "Bloco de questões", "passos": [
        {"minutos": 5, "texto": "Escolha o recorte (subitens abaixo) e separe as questões."},
        {"minutos": 40, "texto": "Resolva cronometrado, no estilo certo/errado: deixe em branco quando não souber."},
        {"minutos": 15, "texto": "Corrija e anote o porquê de cada erro (conceito, pegadinha ou chute)."}
      ]}
    ],
    "essay": [
      {"ate": null, "titulo": "Treino discursivo", "passos": [
        {"minutos": 10, "texto": "Leia o enunciado e monte um esquema por aspecto."},
        {"minutos": 40, "texto": "Escreva respeitando o limite de linhas."},
        {"minutos": 10, "texto": "Revise o português e compare com os pontos esperados."}
      ]}
    ]
  },
  "roteiros_por_bloco": {
    "S13": [
      {"ate": null, "titulo": "Complementares + revisão da semana", "passos": [
        {"minutos": 5, "texto": "Leia os subitens do edital abaixo e escolha o recorte de hoje."},
        {"minutos": 30, "texto": "Leitura dirigida no material indicado."},
        {"minutos": 10, "texto": "Questões do tópico de hoje."},
        {"minutos": 15, "texto": "Revisão da semana: releia as anotações dos blocos de segunda a quinta e marque o que precisa voltar."}
      ]}
    ],
    "S14": [
      {"ate": null, "titulo": "Discursiva de complementares (Q1)", "passos": [
        {"minutos": 10, "texto": "Leia o texto motivador e monte um esquema com um parágrafo por aspecto."},
        {"minutos": 35, "texto": "Escreva a resposta completa, até 30 linhas."},
        {"minutos": 10, "texto": "Revise o português e confira se cada aspecto foi respondido."},
        {"minutos": 5, "texto": "Abra os pontos esperados e anote o que faltou."}
      ]}
    ],
    "S15": [
      {"ate": "2026-11-22", "titulo": "Situação-problema (Q2) — formato reduzido", "passos": [
        {"minutos": 15, "texto": "Esquema completo: o que responder em cada aspecto, com a norma ou boa prática que sustenta."},
        {"minutos": 40, "texto": "Escreva 2 aspectos por extenso (~30 linhas), como na prova."},
        {"minutos": 5, "texto": "Revise e compare o esquema com os pontos esperados."}
      ]},
      {"ate": null, "titulo": "Situação-problema (Q2) — ritmo de prova", "passos": [
        {"minutos": 10, "texto": "Esquema de todos os aspectos."},
        {"minutos": 45, "texto": "Escreva em ritmo de prova (meta: 40 linhas ou mais). A resposta completa de 60 linhas fica para o simulado."},
        {"minutos": 5, "texto": "Compare com os pontos esperados."}
      ]}
    ]
  },
  "primeira_semana": {
    "S13": "Semana parcial: ainda não há anotações da semana para revisar. Use os 15 min finais em mais questões do tópico."
  },
  "subitens": {},
  "materiais": {},
  "lembretes": {
    "complementary": [
      "Até 30 linhas: o que passar do limite não é corrigido.",
      "Fuga ao tema ou texto em branco zera a questão.",
      "NQ1 = NC − 6 × NE ÷ TL: cada erro de português pesa mais em texto curto.",
      "Um parágrafo por aspecto, na ordem do comando.",
      "Apresentação e estrutura textual entram na nota de conteúdo."
    ],
    "technical_case": [
      "Até 60 linhas: o que passar do limite não é corrigido.",
      "Fuga ao tema ou texto em branco zera a questão.",
      "NQ2 = NC − 14 × NE ÷ TL.",
      "Responda com base nos dados do caso, citando norma ou boa prática quando couber.",
      "Na prova, NQ1 + NQ2 precisa chegar a 50."
    ]
  },
  "temas": {"complementary": [], "technical_case": []}
}
```

- [ ] **Step 5: Rodar e ver passar**

Run: `cd apps/api && uv run pytest tests/unit -q`
Expected: todos passam (inclui `3 passed` de `test_guidance_content.py`)

- [ ] **Step 6: Commit**

```bash
git add docs/data/orientacoes.json apps/api/app/guidance apps/api/tests/unit/test_guidance_content.py
git commit -m "feat(api): conteúdo de orientações por bloco com validador

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `occurrences.theme_id`, título novo de S13 e seed que atualiza títulos

**Files:**
- Create: `apps/api/migrations/versions/20261010_5c9e1f3a7b21_occurrence_theme.py`
- Modify: `apps/api/app/models.py` (classe `Occurrence`, perto da linha 136), `apps/api/app/seed.py` (bloco do `template`), `docs/data/ciclo-inicial.json` (slot S13), `docs/02-edital-e-plano.md` (§3, linha de sexta)
- Test: `apps/api/tests/integration/test_seed.py`

**Interfaces:**
- Produces: `Occurrence.theme_id: str | None` (String(16)); seed passa a atualizar `title` dos slots existentes pelo `code`.

- [ ] **Step 1: Teste que falha** — acrescentar em `test_seed.py`:

```python
def test_seed_updates_slot_titles(db):
    slot = db.scalar(select(CycleSlot).where(CycleSlot.code == "S13"))
    assert slot.title == "Complementares + revisão da semana"
    slot.title = "antigo"
    db.commit()
    seed(db)
    db.expire_all()
    assert db.scalar(select(CycleSlot).where(CycleSlot.code == "S13")).title == "Complementares + revisão da semana"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `docker compose --profile test run --rm test pytest -q tests/integration/test_seed.py`
Expected: FAIL em `assert slot.title == "Complementares + revisão da semana"` (ainda é "Complementares e revisão")

- [ ] **Step 3: Implementar**

Em `docs/data/ciclo-inicial.json`, no slot `"code": "S13"`, trocar `"title": "Complementares e revisão"` por `"title": "Complementares + revisão da semana"`. Em `docs/02-edital-e-plano.md` §3, trocar `C02/C04 e revisão` por `C02/C04 + revisão da semana`.

Em `apps/api/app/seed.py`, logo depois do bloco `if template is None: ... db.add(template)`, acrescentar:

```python
    else:
        # Títulos são texto do plano, não dado pessoal: o JSON é a fonte.
        titles = {s["code"]: s["title"] for s in cycle["slots"]}
        for slot in template.slots:
            slot.title = titles.get(slot.code, slot.title)
```

Em `apps/api/app/models.py`, na classe `Occurrence`, depois de `skip_reason`:

```python
    theme_id: Mapped[str | None] = mapped_column(String(16))
```

Criar `apps/api/migrations/versions/20261010_5c9e1f3a7b21_occurrence_theme.py`:

```python
"""occurrence theme

Revision ID: 5c9e1f3a7b21
Revises: 2a16732b4a43
Create Date: 2026-10-10 18:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "5c9e1f3a7b21"
down_revision = "2a16732b4a43"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("occurrences", sa.Column("theme_id", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("occurrences", "theme_id")
```

- [ ] **Step 4: Rodar e ver passar**

Run: `docker compose --profile test run --rm test pytest -q tests/integration`
Expected: todos passam

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/models.py apps/api/app/seed.py apps/api/migrations/versions/20261010_5c9e1f3a7b21_occurrence_theme.py apps/api/tests/integration/test_seed.py docs/data/ciclo-inicial.json docs/02-edital-e-plano.md
git commit -m "feat(api): tema por bloco e S13 vira Complementares + revisão da semana

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: API — `GET /occurrences/{id}/guidance`, troca de tema e tema fixado pela sessão

**Files:**
- Create: `apps/api/app/guidance/service.py`, `apps/api/app/guidance/router.py`
- Modify: `apps/api/app/main.py` (incluir router), `apps/api/app/planning/router.py` (`OccurrencePatch.theme_id`), `apps/api/app/planning/service.py` (`patch_occurrence`), `apps/api/app/study/service.py` (`create_session`)
- Test: `apps/api/tests/integration/test_guidance.py`

**Interfaces:**
- Consumes: `resolve_themes`, `next_theme`, `pick_variant`, `ThemeRef` (Tarefa 1); `content.guidance()` (Tarefa 2); `Occurrence.theme_id` (Tarefa 3); `current_plan`, `session_stats` (`app/planning/service.py`); `suggest_topic`, `week_index` (`app/domain/cycle.py`).
- Produces:
  - `GET /api/v1/occurrences/{id}/guidance` → `{roteiro: {ate, titulo, passos: [{minutos, texto}]}, nota: str | null, topic: {id, title, subitens: [str]} | null, materiais: [{titulo, url, nota}], tema: Tema | null, next_theme_id: str | null, lembretes: [str]}`; 404 `not_found`.
  - `PATCH /api/v1/occurrences/{id}` aceita `theme_id` (≤16 chars). Erros 422: `unknown_theme`, `theme_locked`.
  - `guidance.service.current_theme(db, occ) -> str | None`, `guidance.service.set_theme(db, occ, theme_id) -> None`.

- [ ] **Step 1: Testes que falham** — criar `apps/api/tests/integration/test_guidance.py`:

```python
import copy
import uuid

import pytest

from app.guidance import content


def theme(id, kind="complementary"):
    lines, points = (30, 30) if kind == "complementary" else (60, 70)
    return {"id": id, "titulo": f"Tema {id}", "topic_ids": ["C04.01"], "linhas": lines,
            "texto_motivador": "Texto.", "comando": "Redija um texto dissertativo.",
            "aspectos": [{"texto": "Aspecto", "valor": points}],
            "espelho": {"texto_padrao": "Padrão.", "quesitos": [{"id": "2.1", "texto": "Q", "conceitos": ["0", "1"]}]},
            "fontes": [{"titulo": "Edital", "url": "https://www.in.gov.br/"}], "semelhante_a": None}


@pytest.fixture
def temas(monkeypatch):
    data = copy.deepcopy(content.guidance())
    data["temas"] = {"complementary": [theme("D1"), theme("D2"), theme("D3")],
                     "technical_case": [theme("C1", "technical_case")]}
    data["subitens"] = {"C04.01": ["1.1 Formulação de perguntas"]}
    monkeypatch.setattr(content, "guidance", lambda: data)
    return data


def week(client, start):
    items = client.post("/api/v1/plans/current/weeks", json={"week_start": start}).json()["items"]
    return {i["slot"]["code"]: i for i in items}


def guidance(client, occ):
    return client.get(f"/api/v1/occurrences/{occ['id']}/guidance")


def essay_session(client, occ):
    body = {"id": str(uuid.uuid4()), "occurrence_id": occ["id"], "studied_on": "2026-10-09",
            "duration_minutes": 60, "activity": "essay", "essay_kind": "complementary", "topic_ids": []}
    assert client.post("/api/v1/sessions", json=body).status_code == 201


def test_s13_first_week_has_note_topic_and_subitems(client, temas):
    g = guidance(client, week(client, "2026-10-05")["S13"]).json()
    assert g["roteiro"]["titulo"] == "Complementares + revisão da semana"
    assert g["nota"].startswith("Semana parcial")
    assert g["topic"] == {"id": "C04.01", "title": g["topic"]["title"], "subitens": ["1.1 Formulação de perguntas"]}
    assert (g["tema"], g["next_theme_id"], g["lembretes"]) == (None, None, [])


def test_s13_full_week_has_no_note(client, temas):
    assert guidance(client, week(client, "2026-10-12")["S13"]).json()["nota"] is None


def test_essay_rotation_and_swap(client, temas):
    s14 = week(client, "2026-10-05")["S14"]
    g = guidance(client, s14).json()
    assert (g["tema"]["id"], g["next_theme_id"]) == ("D1", "D2")
    assert g["lembretes"][0].startswith("Até 30 linhas")
    assert guidance(client, week(client, "2026-10-12")["S14"]).json()["tema"]["id"] == "D2"
    r = client.patch(f"/api/v1/occurrences/{s14['id']}", json={"version": s14["version"], "theme_id": "D3"})
    assert r.status_code == 200
    assert guidance(client, s14).json()["tema"]["id"] == "D3"


def test_theme_is_fixed_after_session(client, temas):
    s14 = week(client, "2026-10-05")["S14"]
    swapped = client.patch(f"/api/v1/occurrences/{s14['id']}", json={"version": s14["version"], "theme_id": "D2"}).json()
    essay_session(client, s14)
    g = guidance(client, s14).json()
    assert (g["tema"]["id"], g["next_theme_id"]) == ("D2", None)
    locked = client.patch(f"/api/v1/occurrences/{s14['id']}", json={"version": swapped["version"], "theme_id": "D3"})
    assert locked.json()["error"]["code"] == "theme_locked"
    assert guidance(client, week(client, "2026-10-12")["S14"]).json()["tema"]["id"] == "D3"


def test_session_pins_default_theme(client, temas, db):
    from app.models import Occurrence

    s14 = week(client, "2026-10-05")["S14"]
    essay_session(client, s14)
    db.expire_all()
    assert db.get(Occurrence, uuid.UUID(s14["id"])).theme_id == "D1"


def test_unknown_theme_and_theme_on_theory_block(client, temas):
    w = week(client, "2026-10-05")
    bad = client.patch(f"/api/v1/occurrences/{w['S14']['id']}", json={"version": w["S14"]["version"], "theme_id": "C1"})
    assert bad.json()["error"]["code"] == "unknown_theme"
    theory = client.patch(f"/api/v1/occurrences/{w['S13']['id']}", json={"version": w["S13"]["version"], "theme_id": "D1"})
    assert theory.json()["error"]["code"] == "unknown_theme"


def test_guidance_without_themes(client, temas):
    temas["temas"] = {"complementary": [], "technical_case": []}
    g = guidance(client, week(client, "2026-10-05")["S15"]).json()
    assert g["roteiro"]["titulo"].startswith("Situação-problema (Q2)")
    assert (g["tema"], g["next_theme_id"]) == (None, None)
    assert g["lembretes"][0].startswith("Até 60 linhas")


def test_guidance_does_not_write_and_404(client, temas):
    s14 = week(client, "2026-10-05")["S14"]
    guidance(client, s14)
    again = client.get("/api/v1/occurrences", params={"from": "2026-10-09", "to": "2026-10-09"}).json()["items"]
    assert next(o for o in again if o["id"] == s14["id"])["version"] == s14["version"]
    assert client.get(f"/api/v1/occurrences/{uuid.uuid4()}/guidance").status_code == 404
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `docker compose --profile test run --rm test pytest -q tests/integration/test_guidance.py`
Expected: FAIL (404 na rota de orientação; `theme_id` ignorado)

- [ ] **Step 3: Serviço** — criar `apps/api/app/guidance/service.py`:

```python
"""Orientação de um bloco: roteiro, tópico, materiais e tema discursivo (spec B1–B6)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.cycle import suggest_topic, week_index
from app.domain.guidance import ThemeRef, next_theme, pick_variant, resolve_themes
from app.errors import ApiError
from app.guidance import content
from app.models import CycleSlot, Occurrence, Topic
from app.planning.service import current_plan, session_stats


def essay_kind(occ: Occurrence) -> str | None:
    """complementary | technical_case para S14/S15; None para os demais."""
    return occ.slot.selection_mode if occ.slot.activity == "essay" else None


def _theme_ids(kind: str) -> list[str]:
    return [t["id"] for t in content.guidance()["temas"][kind]]


def _theme_state(db: Session, kind: str) -> tuple[dict[str, str | None], set[str], set[str]]:
    """(tema por ocorrência, temas feitos, ocorrências com sessão)."""
    plan = current_plan(db)
    occs = list(db.scalars(
        select(Occurrence).join(CycleSlot).where(CycleSlot.activity == "essay", CycleSlot.selection_mode == kind)
    ))
    stats = session_stats(db, [o.id for o in occs])
    with_session = {str(o.id) for o in occs if stats.get(o.id, (0, None))[0] > 0}
    refs = [ThemeRef(str(o.id), week_index(o.week_start, plan.starts_on), o.theme_id, str(o.id) in with_session)
            for o in occs]
    resolved = resolve_themes(_theme_ids(kind), refs)
    done = {resolved[oid] for oid in with_session if resolved[oid] is not None}
    return resolved, done, with_session


def current_theme(db: Session, occ: Occurrence) -> str | None:
    kind = essay_kind(occ)
    if kind is None:
        return None
    resolved, _, _ = _theme_state(db, kind)
    return resolved.get(str(occ.id))


def set_theme(db: Session, occ: Occurrence, theme_id: str) -> None:
    kind = essay_kind(occ)
    if kind is None or theme_id not in _theme_ids(kind):
        raise ApiError(422, "unknown_theme", "Tema inexistente para este bloco.", {"theme_id": "Inexistente."})
    _, _, with_session = _theme_state(db, kind)
    if str(occ.id) in with_session:
        raise ApiError(422, "theme_locked", "Este bloco já tem sessão registrada: o tema ficou fixo.")
    occ.theme_id = theme_id


def guidance_out(db: Session, occ: Occurrence) -> dict:
    data = content.guidance()
    slot = occ.slot
    idx = week_index(occ.week_start, current_plan(db).starts_on)
    variants = data["roteiros_por_bloco"].get(slot.code) or data["roteiros_por_atividade"][slot.activity]
    topic_id = suggest_topic(slot.selection_mode, slot.candidate_topic_ids, idx)
    topic = db.get(Topic, topic_id) if topic_id else None
    out = {
        "roteiro": pick_variant(variants, occ.planned_on),
        "nota": data["primeira_semana"].get(slot.code) if idx == 0 else None,
        "topic": {"id": topic.id, "title": topic.title, "subitens": data["subitens"].get(topic.id, [])}
        if topic else None,
        "materiais": data["materiais"].get(topic_id, []) if topic_id else [],
        "tema": None,
        "next_theme_id": None,
        "lembretes": [],
    }
    kind = essay_kind(occ)
    if kind is None:
        return out
    resolved, done, with_session = _theme_state(db, kind)
    themes = {t["id"]: t for t in data["temas"][kind]}
    current = resolved.get(str(occ.id))
    out["tema"] = themes.get(current) if current else None
    out["lembretes"] = data["lembretes"][kind]
    if current and str(occ.id) not in with_session:
        out["next_theme_id"] = next_theme(list(themes), current, done)
    return out
```

- [ ] **Step 4: Rota** — criar `apps/api/app/guidance/router.py`:

```python
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import ApiError
from app.guidance import service
from app.models import Occurrence

router = APIRouter(tags=["guidance"])


@router.get("/occurrences/{occ_id}/guidance")
def get_guidance(occ_id: uuid.UUID, db: Session = Depends(get_db)):
    occ = db.get(Occurrence, occ_id)
    if occ is None:
        raise ApiError(404, "not_found", "Bloco não encontrado.")
    return service.guidance_out(db, occ)
```

Em `apps/api/app/main.py`: `from app.guidance.router import router as guidance_router` e acrescentar `guidance_router` na tupla do `for router in (...)`.

- [ ] **Step 5: Troca de tema no PATCH** — em `apps/api/app/planning/router.py`, em `OccurrencePatch`, acrescentar (e importar `Field` de `pydantic`):

```python
    theme_id: str | None = Field(default=None, max_length=16)
```

Em `apps/api/app/planning/service.py`, em `patch_occurrence`, logo antes de `status = patch.get("status")`:

```python
    if patch.get("theme_id") is not None:
        from app.guidance.service import set_theme  # import tardio: guidance depende de planning

        set_theme(db, occ, patch["theme_id"])
```

- [ ] **Step 6: Sessão fixa o tema** — em `apps/api/app/study/service.py`, importar `from app.guidance.service import current_theme` e, em `create_session`, logo depois do bloco que valida `occurrence` (antes de `session = StudySession(...)`):

```python
    if occurrence is not None and occurrence.theme_id is None and occurrence.slot.activity == "essay":
        # Fixa o tema exibido antes que esta sessão o marque como feito e mude o rodízio.
        occurrence.theme_id = current_theme(db, occurrence)
```

- [ ] **Step 7: Rodar e ver passar**

Run: `docker compose --profile test run --rm test`
Expected: todos passam (inclui `9 passed` de `test_guidance.py`)

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/guidance apps/api/app/main.py apps/api/app/planning apps/api/app/study/service.py apps/api/tests/integration/test_guidance.py
git commit -m "feat(api): orientação por bloco, troca de tema e tema fixado pela sessão

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Web — "Outros blocos de hoje" e "Mover para amanhã"

**Files:**
- Create: `apps/web/src/features/today/MoveTomorrow.tsx`, `apps/web/src/features/today/OtherBlocks.tsx`
- Modify: `apps/web/src/shared/api/types.ts` (`Plan`), `apps/web/src/shared/api/hooks.ts` (`usePlan`, `enabled` em `useOccurrences`), `apps/web/src/features/today/TodayPage.tsx` (`MissionRow` e `TodayPage`)
- Test: `apps/web/src/features/today/OtherBlocks.test.tsx`

**Interfaces:**
- Consumes: `GET /plans/current` (`starts_on`, `ends_on`), `PATCH /occurrences/{id}`.
- Produces: `Plan` type; `usePlan()`; `useOccurrences(from, to, enabled = true)`; `<MoveTomorrowButton occ today />`; `<OtherBlocks view onRegister />`.

- [ ] **Step 1: Teste que falha** — criar `apps/web/src/features/today/OtherBlocks.test.tsx`:

```tsx
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { DayView, Occurrence, OccurrenceStatus } from '../../shared/api/types'
import { renderWithProviders, stubFetch } from '../../test/render'
import { OtherBlocks } from './OtherBlocks'

const occ = (id: string, title: string, status: OccurrenceStatus = 'pending'): Occurrence => ({
  id, version: 2, week_start: '2026-10-05', planned_on: '2026-10-10', window: 'middle', status, skip_reason: null,
  actual_minutes: 0, completed_on: null, suggested_topic_id: null,
  slot: { code: 'S14', title, purpose: 'essay', activity: 'essay', minutes: 60, selection_mode: 'complementary',
    candidate_topic_ids: [] },
})

const view = (date: string, occurrences: Occurrence[]): DayView => ({
  date, kind: 'free', in_plan: true, week_generated: true, xp_today: 0, occurrences,
  mission: { id: 'm', date, kind: 'free', checkout_note: null, complete: true, items: [
    { id: 'i1', position: 0, kind: 'block', ref_id: 'a', required: true, target: null, state: 'done', na_reason: null },
  ] },
})

const plan = (ends_on: string) => ({ match: '/plans/current', body: { id: 'p', starts_on: '2026-10-09', ends_on, exam_date: '2026-12-13' } })

afterEach(() => vi.unstubAllGlobals())

describe('OtherBlocks', () => {
  it('não repete bloco da missão e esconde dispensados', async () => {
    stubFetch([plan('2026-12-12')])
    renderWithProviders(<OtherBlocks view={view('2026-10-10', [occ('a', 'Da missão'), occ('b', 'Remanejado'),
      occ('c', 'Dispensado', 'skipped')])} onRegister={() => {}} />)
    expect(screen.getByText(/Remanejado/)).toBeInTheDocument()
    expect(screen.queryByText(/Da missão/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Dispensado/)).not.toBeInTheDocument()
  })

  it('registra sessão e move para amanhã mantendo a janela', async () => {
    const fetchMock = stubFetch([plan('2026-12-12'),
      { method: 'PATCH', match: '/occurrences/b', body: { game_delta: null } }])
    const onRegister = vi.fn()
    renderWithProviders(<OtherBlocks view={view('2026-10-10', [occ('b', 'Remanejado')])} onRegister={onRegister} />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Registrar sessão' }))
    expect(onRegister).toHaveBeenCalledWith(expect.objectContaining({ id: 'b' }))
    await user.click(await screen.findByRole('button', { name: 'Mover para amanhã' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(true))
    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')!
    expect(JSON.parse(patch[1]!.body as string)).toEqual({ version: 2, planned_on: '2026-10-11' })
  })

  it('"Mover para amanhã" some no último dia do plano', async () => {
    stubFetch([plan('2026-12-12')])
    renderWithProviders(<OtherBlocks view={view('2026-12-12', [occ('b', 'Remanejado')])} onRegister={() => {}} />)
    await screen.findByRole('button', { name: 'Registrar sessão' })
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Mover para amanhã' })).not.toBeInTheDocument())
  })

  it('não aparece sem missão aberta', () => {
    stubFetch([plan('2026-12-12')])
    const v = { ...view('2026-10-10', [occ('b', 'Remanejado')]), mission: null }
    const { container } = renderWithProviders(<OtherBlocks view={v} onRegister={() => {}} />)
    expect(container).toBeEmptyDOMElement()
  })
})
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd apps/web && npx vitest run src/features/today/OtherBlocks.test.tsx`
Expected: FAIL com `Failed to resolve import "./OtherBlocks"`

- [ ] **Step 3: Tipos e hooks** — em `types.ts`:

```ts
export interface Plan { id: string; starts_on: string; ends_on: string; exam_date: string }
```

Em `hooks.ts`, importar `Plan` e:

```ts
export const usePlan = () =>
  useQuery({ queryKey: ['plan'], queryFn: () => api<Plan>('/plans/current'), staleTime: Infinity })
```

e trocar `useOccurrences` por:

```ts
export const useOccurrences = (from: string, to: string, enabled = true) =>
  useQuery({
    queryKey: ['occurrences', from, to],
    queryFn: () => api<ListResponse<Occurrence>>(`/occurrences?from=${from}&to=${to}`),
    enabled,
  })
```

- [ ] **Step 4: Componentes** — criar `apps/web/src/features/today/MoveTomorrow.tsx`:

```tsx
import { usePatchOccurrence, usePlan } from '../../shared/api/hooks'
import type { Occurrence } from '../../shared/api/types'
import { addDays } from '../../shared/format'

/** Atalho: move o bloco para o dia seguinte, mesma janela. Some se amanhã passar do fim do plano. */
export function MoveTomorrowButton({ occ, today }: { occ: Occurrence; today: string }) {
  const plan = usePlan()
  const patch = usePatchOccurrence()
  const tomorrow = addDays(today, 1)
  if (!plan.data || tomorrow > plan.data.ends_on) return null
  return (
    <>
      <button onClick={() => patch.mutate({ id: occ.id, body: { version: occ.version, planned_on: tomorrow } })}
        disabled={patch.isPending} className="px-3 py-1 text-sm text-primary">
        Mover para amanhã
      </button>
      {patch.error && <p role="alert" className="w-full text-sm text-destructive">{patch.error.message}</p>}
    </>
  )
}
```

Criar `apps/web/src/features/today/OtherBlocks.tsx`:

```tsx
import type { DayView, Occurrence } from '../../shared/api/types'
import { WINDOW_LABEL } from '../../shared/format'
import { MoveTomorrowButton } from './MoveTomorrow'

/** Blocos do dia que ficaram fora da missão (entraram depois de o dia ser aberto). */
export function OtherBlocks({ view, onRegister }: { view: DayView; onRegister: (o: Occurrence) => void }) {
  if (!view.mission) return null
  const inMission = new Set(view.mission.items.map((i) => i.ref_id))
  const others = view.occurrences.filter((o) => !inMission.has(o.id) && o.status !== 'skipped')
  if (others.length === 0) return null
  return (
    <section aria-label="Outros blocos de hoje" className="rounded-lg border border-border bg-card p-4">
      <h2 className="font-semibold">Outros blocos de hoje</h2>
      <p className="text-xs text-muted-foreground">Fora da missão: dão XP e concluem o bloco, mas não contam para a missão.</p>
      <ul className="mt-2 space-y-2">
        {others.map((o) => (
          <li key={o.id} className="flex flex-wrap items-center gap-2 rounded-md bg-muted p-3">
            <div className="min-w-0 flex-1">
              <p className="font-semibold">{WINDOW_LABEL[o.window]} · {o.slot.title}</p>
              <p className="text-xs text-muted-foreground">{o.status === 'completed' ? '✓ Feito' : 'Pendente'}</p>
            </div>
            {o.status === 'pending' && (
              <>
                <button onClick={() => onRegister(o)} className="rounded-md bg-primary px-3 py-1 text-sm text-primary-foreground">
                  Registrar sessão
                </button>
                <MoveTomorrowButton occ={o} today={view.date} />
              </>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
```

- [ ] **Step 5: Ligar na tela Hoje** — em `TodayPage.tsx`:
  - importar `OtherBlocks` e `MoveTomorrowButton`;
  - logo depois de `<MissionCard ... />` (dentro do ramo `view.mission ?`), trocar o ramo por um fragmento com `<MissionCard view={view} onRegister={(o) => setForm({ occurrence: o })} />` seguido de `<OtherBlocks view={view} onRegister={(o) => setForm({ occurrence: o })} />`;
  - em `MissionRow`, entre o botão "Não se aplica hoje" e o `<Link ...>Remanejar</Link>`, inserir `<MoveTomorrowButton occ={occ} today={view.date} />`.

- [ ] **Step 6: Rodar e ver passar**

Run: `cd apps/web && npm test`
Expected: todos passam

- [ ] **Step 7: Commit**

```bash
git add apps/web/src
git commit -m "feat(web): outros blocos de hoje e atalho Mover para amanhã

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Web — aviso de blocos atrasados

**Files:**
- Create: `apps/web/src/features/today/LateBlocks.tsx`
- Modify: `apps/web/src/features/today/TodayPage.tsx`
- Test: `apps/web/src/features/today/LateBlocks.test.tsx`

**Interfaces:**
- Consumes: `usePlan`, `useOccurrences(from, to, enabled)` (Tarefa 5), `usePatchOccurrence`.
- Produces: `<LateBlocks today />`.

- [ ] **Step 1: Teste que falha** — criar `apps/web/src/features/today/LateBlocks.test.tsx`:

```tsx
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Occurrence, OccurrenceStatus } from '../../shared/api/types'
import { renderWithProviders, stubFetch } from '../../test/render'
import { LateBlocks } from './LateBlocks'

const occ = (id: string, title: string, status: OccurrenceStatus = 'pending'): Occurrence => ({
  id, version: 4, week_start: '2026-10-05', planned_on: '2026-10-09', window: 'after', status, skip_reason: null,
  actual_minutes: 0, completed_on: null, suggested_topic_id: null,
  slot: { code: 'S15', title, purpose: 'essay', activity: 'essay', minutes: 60, selection_mode: 'technical_case',
    candidate_topic_ids: [] },
})

const plan = { match: '/plans/current', body: { id: 'p', starts_on: '2026-10-09', ends_on: '2026-12-12', exam_date: '2026-12-13' } }

afterEach(() => vi.unstubAllGlobals())

describe('LateBlocks', () => {
  it('conta só pendentes e traz os escolhidos para hoje', async () => {
    const fetchMock = stubFetch([plan,
      { match: '/occurrences?from=2026-10-09&to=2026-10-11',
        body: { items: [occ('x', 'Situação-problema de TI'), occ('y', 'Dispensado', 'skipped')], total: 2 } },
      { method: 'PATCH', match: '/occurrences/x', body: { game_delta: null } }])
    renderWithProviders(<LateBlocks today="2026-10-12" />)
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: /1 bloco atrasado/ }))
    expect(screen.queryByLabelText(/Dispensado/)).not.toBeInTheDocument()
    const bring = screen.getByRole('button', { name: 'Trazer para hoje' })
    expect(bring).toBeDisabled()
    await user.click(screen.getByLabelText(/Situação-problema de TI/))
    await user.click(bring)
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(true))
    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')!
    expect(JSON.parse(patch[1]!.body as string)).toEqual({ version: 4, planned_on: '2026-10-12' })
  })

  it('não consulta no primeiro dia do plano', async () => {
    const fetchMock = stubFetch([plan])
    const { container } = renderWithProviders(<LateBlocks today="2026-10-09" />)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/plans/current', expect.anything()))
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/occurrences'))).toBe(false)
    expect(container).toBeEmptyDOMElement()
  })
})
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd apps/web && npx vitest run src/features/today/LateBlocks.test.tsx`
Expected: FAIL com `Failed to resolve import "./LateBlocks"`

- [ ] **Step 3: Implementar** — criar `apps/web/src/features/today/LateBlocks.tsx`:

```tsx
import { useState } from 'react'

import { useOccurrences, usePatchOccurrence, usePlan } from '../../shared/api/hooks'
import { addDays, formatDay } from '../../shared/format'

/** Aviso de blocos pendentes em dias passados; o usuário escolhe quais trazer para hoje. */
export function LateBlocks({ today }: { today: string }) {
  const plan = usePlan()
  const yesterday = addDays(today, -1)
  const startsOn = plan.data?.starts_on ?? today
  const enabled = !!plan.data && yesterday >= startsOn
  const { data } = useOccurrences(startsOn, yesterday, enabled)
  const patch = usePatchOccurrence()
  const [open, setOpen] = useState(false)
  const [chosen, setChosen] = useState<string[]>([])
  const late = (data?.items ?? []).filter((o) => o.status === 'pending')
  if (!enabled || late.length === 0) return null

  const toggle = (id: string) => setChosen((c) => (c.includes(id) ? c.filter((x) => x !== id) : [...c, id]))
  async function bring() {
    try {
      for (const o of late.filter((o) => chosen.includes(o.id))) {
        await patch.mutateAsync({ id: o.id, body: { version: o.version, planned_on: today } })
      }
      setChosen([])
      setOpen(false)
    } catch {
      // A mensagem aparece via patch.error.
    }
  }

  const n = late.length
  return (
    <section className="rounded-md border border-border bg-card p-3 text-sm">
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="font-semibold text-streak">
        {n} {n === 1 ? 'bloco atrasado' : 'blocos atrasados'} — escolher quais trazer para hoje
      </button>
      {open && (
        <fieldset className="mt-2 space-y-1">
          <legend className="sr-only">Blocos atrasados</legend>
          {late.map((o) => (
            <label key={o.id} className="flex items-center gap-2">
              <input type="checkbox" checked={chosen.includes(o.id)} onChange={() => toggle(o.id)} />
              {formatDay(o.planned_on)} · {o.slot.title}
            </label>
          ))}
          <button onClick={bring} disabled={chosen.length === 0 || patch.isPending}
            className="mt-2 rounded-md bg-primary px-3 py-1 text-primary-foreground disabled:opacity-50">
            Trazer para hoje
          </button>
        </fieldset>
      )}
      {patch.error && <p role="alert" className="mt-2 text-destructive">{patch.error.message}</p>}
    </section>
  )
}
```

Em `TodayPage.tsx`, importar `LateBlocks` e renderizar `{view.in_plan && <LateBlocks today={today} />}` logo depois de `<StreakHint />`.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd apps/web && npm test`
Expected: todos passam

- [ ] **Step 5: Commit**

```bash
git add apps/web/src
git commit -m "feat(web): aviso de blocos atrasados com escolha do que trazer para hoje

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Web — painel "Como fazer este bloco"

**Files:**
- Create: `apps/web/src/features/guidance/GuidancePanel.tsx`
- Modify: `apps/web/src/shared/api/types.ts` (`Guidance`, `Theme`), `apps/web/src/shared/api/hooks.ts` (`useGuidance`; `'guidance'` na invalidação), `apps/web/src/features/today/TodayPage.tsx` (`MissionRow`), `apps/web/src/features/today/OtherBlocks.tsx`, `apps/web/src/features/cycle/CyclePage.tsx` (`OccurrenceRow`)
- Test: `apps/web/src/features/guidance/GuidancePanel.test.tsx`

**Interfaces:**
- Consumes: `GET /occurrences/{id}/guidance`, `PATCH /occurrences/{id}` com `theme_id` (Tarefa 4).
- Produces: `<GuidancePanel occ />`; `useGuidance(id, enabled)`.

- [ ] **Step 1: Teste que falha** — criar `apps/web/src/features/guidance/GuidancePanel.test.tsx`:

```tsx
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Guidance, Occurrence } from '../../shared/api/types'
import { renderWithProviders, stubFetch } from '../../test/render'
import { GuidancePanel } from './GuidancePanel'

const occ: Occurrence = {
  id: 'o1', version: 5, week_start: '2026-10-05', planned_on: '2026-10-11', window: 'middle', status: 'pending',
  skip_reason: null, actual_minutes: 0, completed_on: null, suggested_topic_id: null,
  slot: { code: 'S14', title: 'Discursiva de complementares', purpose: 'essay', activity: 'essay', minutes: 60,
    selection_mode: 'complementary', candidate_topic_ids: [] },
}

const essay: Guidance = {
  roteiro: { ate: null, titulo: 'Discursiva de complementares (Q1)', passos: [{ minutos: 10, texto: 'Monte o esquema.' }] },
  nota: null, topic: null, materiais: [], next_theme_id: 'D2', lembretes: ['Até 30 linhas: o que passar do limite não é corrigido.'],
  tema: { id: 'D1', titulo: 'Transparência ativa', topic_ids: ['C02.01'], linhas: 30, texto_motivador: 'A LAI…',
    comando: 'Redija um texto dissertativo abordando:', aspectos: [{ texto: 'conceito de transparência ativa', valor: 10 }],
    espelho: { texto_padrao: 'Espera-se que…', quesitos: [{ id: '2.1', texto: 'Conceito', conceitos: ['Conceito 0 – não abordou'] }] },
    fontes: [{ titulo: 'Lei 12.527/2011', url: 'https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm' }],
    semelhante_a: null },
}

afterEach(() => vi.unstubAllGlobals())

describe('GuidancePanel', () => {
  it('só busca ao abrir e esconde o espelho até pedir', async () => {
    const fetchMock = stubFetch([{ match: '/occurrences/o1/guidance', body: essay }])
    renderWithProviders(<GuidancePanel occ={occ} />)
    expect(fetchMock).not.toHaveBeenCalled()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Como fazer este bloco' }))
    expect(await screen.findByText('Transparência ativa')).toBeInTheDocument()
    expect(screen.getByText(/\[valor: 10,00 pontos\]/)).toBeInTheDocument()
    expect(screen.getByText(/o que passar do limite/)).toBeInTheDocument()
    expect(screen.queryByText('Espera-se que…')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Ver pontos esperados' }))
    expect(screen.getByText('Espera-se que…')).toBeInTheDocument()
  })

  it('troca o tema com a versão do bloco', async () => {
    const fetchMock = stubFetch([{ match: '/occurrences/o1/guidance', body: essay },
      { method: 'PATCH', match: '/occurrences/o1', body: { game_delta: null } }])
    renderWithProviders(<GuidancePanel occ={occ} />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Como fazer este bloco' }))
    await user.click(await screen.findByRole('button', { name: 'Trocar tema' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(true))
    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')!
    expect(JSON.parse(patch[1]!.body as string)).toEqual({ version: 5, theme_id: 'D2' })
  })

  it('omite seções vazias', async () => {
    const plain: Guidance = { ...essay, tema: null, next_theme_id: null, lembretes: [],
      topic: { id: 'C04.01', title: 'Perguntas e fontes', subitens: [] } }
    stubFetch([{ match: '/occurrences/o1/guidance', body: plain }])
    renderWithProviders(<GuidancePanel occ={occ} />)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Como fazer este bloco' }))
    expect(await screen.findByText(/Perguntas e fontes/)).toBeInTheDocument()
    expect(screen.queryByText('Materiais')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Trocar tema' })).not.toBeInTheDocument()
    expect(screen.queryByText('Regras do edital')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd apps/web && npx vitest run src/features/guidance/GuidancePanel.test.tsx`
Expected: FAIL com `Failed to resolve import "./GuidancePanel"`

- [ ] **Step 3: Tipos e hook** — em `types.ts`:

```ts
export interface GuidanceStep { minutos: number; texto: string }

export interface Theme {
  id: string
  titulo: string
  topic_ids: string[]
  linhas: number
  texto_motivador: string
  comando: string
  aspectos: { texto: string; valor: number }[]
  espelho: { texto_padrao: string; quesitos: { id: string; texto: string; conceitos: string[] }[] }
  fontes: { titulo: string; url: string }[]
  semelhante_a: { prova: string; url: string } | null
}

export interface Guidance {
  roteiro: { ate: string | null; titulo: string; passos: GuidanceStep[] }
  nota: string | null
  topic: { id: string; title: string; subitens: string[] } | null
  materiais: { titulo: string; url: string; nota: string }[]
  tema: Theme | null
  next_theme_id: string | null
  lembretes: string[]
}
```

Em `hooks.ts`, importar `Guidance` e:

```ts
export const useGuidance = (occurrenceId: string, enabled: boolean) =>
  useQuery({
    queryKey: ['guidance', occurrenceId],
    queryFn: () => api<Guidance>(`/occurrences/${occurrenceId}/guidance`),
    enabled,
  })
```

e acrescentar `'guidance'` à lista de chaves invalidadas em `useGameMutation`.

- [ ] **Step 4: Componente** — criar `apps/web/src/features/guidance/GuidancePanel.tsx`:

```tsx
import { useState } from 'react'

import { useGuidance, usePatchOccurrence } from '../../shared/api/hooks'
import type { Guidance, Occurrence, Theme } from '../../shared/api/types'

const points = (v: number) => v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/** Painel recolhível com roteiro, tópico, materiais e, nas discursivas, tema e espelho. */
export function GuidancePanel({ occ }: { occ: Occurrence }) {
  const [open, setOpen] = useState(false)
  const { data, error } = useGuidance(occ.id, open)
  return (
    <div className="w-full">
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="text-sm text-primary">
        {open ? 'Ocultar orientações' : 'Como fazer este bloco'}
      </button>
      {open && !data && !error && <p aria-busy="true" className="text-sm text-muted-foreground">Carregando…</p>}
      {open && error && <p role="alert" className="text-sm text-destructive">{error.message}</p>}
      {open && data && <GuidanceBody occ={occ} g={data} />}
    </div>
  )
}

function GuidanceBody({ occ, g }: { occ: Occurrence; g: Guidance }) {
  return (
    <div className="mt-2 space-y-3 text-sm">
      <section>
        <h3 className="font-semibold">{g.roteiro.titulo}</h3>
        <ol className="mt-1 space-y-1">
          {g.roteiro.passos.map((p, i) => (
            <li key={i}><span className="num">{p.minutos} min</span> · {p.texto}</li>
          ))}
        </ol>
        {g.nota && <p className="mt-1 text-muted-foreground">{g.nota}</p>}
      </section>
      {g.topic && (
        <section>
          <h3 className="font-semibold"><span className="num">{g.topic.id}</span> · {g.topic.title}</h3>
          {g.topic.subitens.length > 0 && (
            <ul className="mt-1 list-disc pl-5 text-muted-foreground">
              {g.topic.subitens.map((s) => <li key={s}>{s}</li>)}
            </ul>
          )}
        </section>
      )}
      {g.materiais.length > 0 && (
        <section>
          <h3 className="font-semibold">Materiais</h3>
          <ul className="mt-1 space-y-1">
            {g.materiais.map((m) => (
              <li key={m.url}>
                <a href={m.url} target="_blank" rel="noreferrer" className="text-primary underline">{m.titulo}</a>
                {m.nota && <span className="text-muted-foreground"> — {m.nota}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}
      {g.tema && <ThemeView key={g.tema.id} occ={occ} tema={g.tema} nextId={g.next_theme_id} />}
      {g.lembretes.length > 0 && (
        <section>
          <h3 className="font-semibold">Regras do edital</h3>
          <ul className="mt-1 list-disc pl-5 text-muted-foreground">
            {g.lembretes.map((l) => <li key={l}>{l}</li>)}
          </ul>
        </section>
      )}
    </div>
  )
}

function ThemeView({ occ, tema, nextId }: { occ: Occurrence; tema: Theme; nextId: string | null }) {
  const [showKey, setShowKey] = useState(false)
  const patch = usePatchOccurrence()
  return (
    <section className="space-y-2 rounded-md border border-border p-3">
      <h3 className="font-semibold">{tema.titulo}</h3>
      <p className="text-xs text-muted-foreground">
        Até <span className="num">{tema.linhas}</span> linhas
        {tema.semelhante_a && (
          <> · semelhante a <a href={tema.semelhante_a.url} target="_blank" rel="noreferrer" className="underline">{tema.semelhante_a.prova}</a></>
        )}
      </p>
      <p className="whitespace-pre-line">{tema.texto_motivador}</p>
      <p className="font-semibold">{tema.comando}</p>
      <ol className="space-y-1">
        {tema.aspectos.map((a, i) => (
          <li key={i}><span className="num">{i + 1}</span> {a.texto} <span className="num text-muted-foreground">[valor: {points(a.valor)} pontos]</span></li>
        ))}
      </ol>
      <p className="text-xs text-muted-foreground">
        Fontes: {tema.fontes.map((f, i) => (
          <span key={f.url}>{i > 0 && '; '}<a href={f.url} target="_blank" rel="noreferrer" className="underline">{f.titulo}</a></span>
        ))}
      </p>
      <div className="flex flex-wrap gap-2">
        {!showKey && (
          <button onClick={() => setShowKey(true)} className="rounded-md bg-muted px-3 py-1">Ver pontos esperados</button>
        )}
        {nextId && (
          <button onClick={() => patch.mutate({ id: occ.id, body: { version: occ.version, theme_id: nextId } })}
            disabled={patch.isPending} className="px-3 py-1 text-primary">Trocar tema</button>
        )}
      </div>
      {patch.error && <p role="alert" className="text-destructive">{patch.error.message}</p>}
      {showKey && (
        <div aria-label="Pontos esperados" className="space-y-2 rounded-md bg-muted p-3">
          <p className="whitespace-pre-line">{tema.espelho.texto_padrao}</p>
          <ol className="space-y-1">
            {tema.espelho.quesitos.map((q) => (
              <li key={q.id}>
                <span className="num">{q.id}</span> {q.texto}
                <ul className="list-disc pl-5 text-muted-foreground">{q.conceitos.map((c) => <li key={c}>{c}</li>)}</ul>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  )
}
```

- [ ] **Step 5: Ligar nas linhas de bloco**
  - `TodayPage.tsx`, `MissionRow`: depois do bloco `{item.state === 'pending' && occ && (...)}`, acrescentar `{occ && <GuidancePanel occ={occ} />}`.
  - `OtherBlocks.tsx`: dentro do `<li>`, por último, `<GuidancePanel occ={o} />`.
  - `CyclePage.tsx`, `OccurrenceRow`: logo antes de `{moving && (`, acrescentar `<GuidancePanel occ={occ} />` dentro de `<div className="mt-2">`.
  - Importar `GuidancePanel` de `../guidance/GuidancePanel` nos três arquivos.

- [ ] **Step 6: Rodar e ver passar**

Run: `cd apps/web && npm test && npm run lint && npm run build`
Expected: testes passam, lint sem erros, build ok

- [ ] **Step 7: Commit**

```bash
git add apps/web/src
git commit -m "feat(web): painel Como fazer este bloco com tema, espelho e troca de tema

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Conteúdo — subitens dos 68 tópicos e materiais de 12/10 a 25/10

**Files:**
- Modify: `docs/data/orientacoes.json` (`subitens`, `materiais`), `apps/api/tests/unit/test_guidance_content.py`

**Interfaces:**
- Consumes: validador da Tarefa 2.
- Produces: `subitens` com os 68 IDs do catálogo; `materiais` para os 15 tópicos sugeridos nas semanas de 12/10 e 19/10: `B01.01, B02.01, B03.01, B04.01, C01.01, C02.01, C03.01, C04.01, C05.01, E01.01, E01.02, E01.04, E02.01, E03.01, E04.01`.

- [ ] **Step 1: Teste que falha** — acrescentar em `test_guidance_content.py`:

```python
NEXT_TWO_WEEKS = {"B01.01", "B02.01", "B03.01", "B04.01", "C01.01", "C02.01", "C03.01", "C04.01", "C05.01",
                  "E01.01", "E01.02", "E01.04", "E02.01", "E03.01", "E04.01"}


def test_every_topic_has_subitems():
    data = content.guidance()
    assert set(data["subitens"]) == catalog_topic_ids()
    assert all(data["subitens"][t] for t in data["subitens"])


def test_next_two_weeks_have_materials():
    assert NEXT_TWO_WEEKS <= set(content.guidance()["materiais"])
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd apps/api && uv run pytest tests/unit/test_guidance_content.py -q`
Expected: FAIL nos 2 testes novos

- [ ] **Step 3: Extrair o texto do edital** — no scratchpad da sessão (não no repo), criar `extract.swift`:

```swift
import PDFKit
let doc = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1]))!
print(doc.string ?? "")
```

Run: `swift "$SCRATCH/extract.swift" docs/edital.pdf > "$SCRATCH/edital.txt" && grep -n "15.2" "$SCRATCH/edital.txt" | head`
Expected: linhas da seção 15.2 (conhecimentos gerais, complementares e específicos).

- [ ] **Step 4: Preencher `subitens`** — para cada tópico do catálogo, usar o `source_ref` (ex.: `15.2.3 / Fundamentos de evidências, dados e IA / tópico 1`) para achar o trecho em `edital.txt` e copiar **literalmente** os subitens do tópico (um item por subitem numerado; se o tópico não tiver subitens numerados, um único item com o texto do tópico). Não resumir. Conferir no PDF qualquer trecho com quebra de linha estranha.

- [ ] **Step 5: Preencher `materiais`** — para cada um dos 15 tópicos, 1 a 3 fontes oficiais (lei/decreto no planalto.gov.br, manuais e guias da CGU/TCU/Casa Civil, documentação oficial da tecnologia), com `nota` dizendo a seção a ler. Para `C04.01`, usar as três de `conteudo/c0401 - perguntas e fontes/materiais para estudo.rtf`. Abrir cada URL (WebFetch) e confirmar que responde e trata do assunto; descartar a que não abrir.

- [ ] **Step 6: Rodar e ver passar**

Run: `cd apps/api && uv run pytest tests/unit -q`
Expected: todos passam

- [ ] **Step 7: Commit**

```bash
git add docs/data/orientacoes.json apps/api/tests/unit/test_guidance_content.py
git commit -m "docs(data): subitens do edital e materiais das próximas duas semanas

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Conteúdo — 10 temas de Q1 e 10 casos de Q2, com revisão do usuário

**Files:**
- Modify: `docs/data/orientacoes.json` (`temas`), `apps/api/tests/unit/test_guidance_content.py`

**Interfaces:**
- Consumes: formato de Tema (Tarefa 2), validador.
- Produces: `temas.complementary` com ≥ 10 temas (`Q1-01`…) e `temas.technical_case` com ≥ 10 casos (`Q2-01`…).

- [ ] **Step 1: Teste que falha** — acrescentar em `test_guidance_content.py`:

```python
def test_enough_themes_until_exam():
    temas = content.guidance()["temas"]
    assert len(temas["complementary"]) >= 10
    assert len(temas["technical_case"]) >= 10
    subjects = {t.split(".")[0] for th in temas["complementary"] for t in th["topic_ids"]}
    assert subjects == {"C01", "C02", "C03", "C04", "C05"}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd apps/api && uv run pytest tests/unit/test_guidance_content.py::test_enough_themes_until_exam -q`
Expected: FAIL (`0 >= 10`)

- [ ] **Step 3: Pesquisar e redigir**
  - **Q1 (S14):** 10 temas cobrindo C01–C05 (2 por disciplina), cada um com texto motivador curto, comando "Redija um texto dissertativo… abordando os seguintes aspectos:", 3 aspectos valorados somando 30 e espelho com texto-padrão citando a norma e um quesito 2.x por aspecto, com conceitos de 0 a N no padrão Cebraspe ("não abordou ou abordou de forma totalmente equivocada" … "abordou corretamente").
  - **Q2 (S15):** 10 casos de órgão público com dados concretos, distribuídos em E01–E04 + contratação de TIC (Lei 14.133/2021, IN SGD/ME 94/2022) e LGPD, puxando para Java/Spring, segurança e integração de IA. Cada caso com 3 a 5 aspectos valorados somando 70.
  - Fontes: só oficiais (planalto.gov.br, gov.br/cgu, TCU, Cebraspe). `semelhante_a` só quando o tema corresponder a uma prova real com URL (ex.: TCDF 2024 e TCE-PR 2024 Auditor TI, Cebraspe). Caso contrário, `null`.

- [ ] **Step 4: Documento de revisão** — publicar os 20 temas, com espelho, num documento (Claude Docs; carregar o skill `anthropic-skills:docs` antes) com uma seção por tema e enviar o link ao usuário.

- [ ] **Step 5: PARAR e esperar a revisão do usuário.** Aplicar os comentários no documento. Só seguir com aprovação explícita.

- [ ] **Step 6: Copiar os temas aprovados para `temas` no JSON** e rodar:

Run: `cd apps/api && uv run pytest tests/unit -q`
Expected: todos passam

- [ ] **Step 7: Commit**

```bash
git add docs/data/orientacoes.json apps/api/tests/unit/test_guidance_content.py
git commit -m "docs(data): temas de Q1 e casos de Q2 no formato Cebraspe

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Documentação, verificação completa e deploy local

**Files:**
- Modify: `docs/10-gamificacao-e-rotina.md` (§ missão: "Outros blocos de hoje" e atrasados), `docs/06-ux-e-fluxos.md` (tela Hoje e Ciclo: painel de orientação, Mover para amanhã, atrasados), `docs/05-arquitetura-e-contratos.md` (rota de orientação e `theme_id` no PATCH)

- [ ] **Step 1: Atualizar os três documentos** com o comportamento da spec (A1–A4, B1–B6), um parágrafo por seção afetada, apontando para `docs/superpowers/specs/2026-10-10-blocos-e-orientacoes.md`.

- [ ] **Step 2: Verificação completa**

Run: `docker compose --profile test run --rm test && (cd apps/web && npm test && npm run lint && npm run build)`
Expected: tudo passa

- [ ] **Step 3: Subir a versão nova** (o volume de dados é preservado; a migração e o seed rodam no start)

Run: `docker compose up -d --build app && curl -s 127.0.0.1:8080/api/v1/health`
Expected: `{"status":"ok"}`

- [ ] **Step 4: Conferir com os dados reais** — com o app no ar, em 11/10:
  - `curl -s 127.0.0.1:8080/api/v1/days/2026-10-11` mostra os dois blocos pendentes;
  - `GET /occurrences/{id}/guidance` de "Discursiva de complementares" traz tema e lembretes;
  - na tela Ciclo, o bloco de sexta 09/10 aparece como "Complementares + revisão da semana".

- [ ] **Step 5: Atualizar o grafo e commitar**

Run: `graphify update .`

```bash
git add docs
git commit -m "docs: blocos fora da missão, atrasados e orientações por bloco

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
