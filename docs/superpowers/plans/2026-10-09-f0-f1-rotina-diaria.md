# F0+F1 — Rotina diária gamificada: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar a v1 utilizável hoje: subir o app com um comando, abrir o dia, cumprir a missão registrando sessões e ver XP, nível e sequência no Mac e no celular.

**Architecture:** Monólito FastAPI que serve o React compilado, com PostgreSQL, tudo em `docker compose` no Mac. Regras de ciclo, missão, XP e sequência são funções puras em `apps/api/app/domain/`, testadas sem banco. A camada `app/game/` monta fatos a partir do banco, chama essas funções e devolve `game_delta` em cada mutação. Nada de jogo é persistido.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.1, psycopg 3, Alembic, pytest, uv · Node 24, Vite 8, React 19, TypeScript 6, React Router 7, TanStack Query 5, Tailwind CSS 4, Vitest 5, Testing Library · PostgreSQL 17.6 · Docker Compose.

**Spec:** `docs/01-PRD.md`, `docs/03-regras-de-negocio.md` (R02, R03, R09, R10, R13, R14), `docs/04-modelo-de-dominio.md`, `docs/05-arquitetura-e-contratos.md`, `docs/06-ux-e-fluxos.md`, `docs/10-gamificacao-e-rotina.md`. Escopo: fatias F0 e F1 de `docs/07-plano-de-implementacao.md`. F2–F5 terão planos próprios depois de 2 dias de uso real.

**Procedência do código:** todo o código deste plano foi executado num protótipo em 09/10/2026. Resultados: 74 testes de backend (pytest no container), 4 testes de frontend (Vitest), `tsc -b` + `vite build`, `alembic check` sem diferenças, seed rodado 2×, stack subindo com `docker compose up -d --build`, jornada pela API, reinício sem perda e restauração de backup. As versões acima são as que o `uv`/`npm` resolveram nessa data. Os lockfiles fixam o que for resolvido na execução.

## Global Constraints

- Usuário único, sem login; porta publicada só em `127.0.0.1:8080`; acesso remoto só via `tailscale serve` (nunca `funnel`); Postgres sem porta publicada.
- `ALLOWED_HOSTS` controla Host e Origin; mutações POST/PUT/PATCH exigem `Content-Type: application/json` (415); Origin fora da lista → 403; Host fora da lista → 400.
- Fuso `America/Sao_Paulo`; “hoje” vem sempre de `app.clock.get_today` (dependência substituível nos testes); datas civis `YYYY-MM-DD`; instantes UTC.
- Plano 09/10/2026–11/12/2026; template inicial `effective_from = 2026-10-05`; semana inicial parcial só com S13–S15 em 09/10; 15 slots de 60 min nas semanas cheias (420/180/180/120).
- Criação com UUID gerado pelo cliente: mesmo `id` + mesmo conteúdo → 200 com o original; conteúdo diferente → 409 `duplicate_id_conflict`. Edições exigem `version` (409 `version_conflict`).
- Sessão: 1–720 min; `studied_on` ≤ hoje; tópicos obrigatórios, exceto `activity=essay`, que exige `essay_kind`.
- Jogo 100% derivado: XP por minuto (teto 240/dia), +20 bloco, +50 missão, +10 item opcional, +150 semana completa, +20 fim de semana ≥ 30 min; nível *n*→*n+1* custa `100·n`; sequência em dias úteis com ≥ 30 min, folga neutra, congelamento por semana completa (máx. 2).
- Erros no formato `{"error":{"code","message","request_id","fields"}}`; textos de interface em pt-BR conforme `docs/06`.
- Sem IA, login, offline, notificações, questões, revisões ou discursivas com rubrica nesta entrega (F2+).
- Dependências fixadas por `uv.lock` e `package-lock.json`; não atualizar por rotina.

## Review Focus

Entradas e condições que a especificação implica e que o uso real vai produzir. Cada uma tem teste na tarefa dona.

1. **Clique duplo ou dois aparelhos em “Abrir o dia”** → uma única missão e resposta 200, nunca erro 500 de unicidade (Tarefa 10, `test_concurrent_open_day_returns_existing_mission`).
2. **“Gerar semana” concorrente** → as mesmas 15 ocorrências e resposta 200 (Tarefa 7, `test_concurrent_week_generation_returns_existing_week`).
3. **Editar a data de uma sessão que concluiu o bloco** → a missão do dia original deixa de estar completa e o XP de missão sai (Tarefa 10, `test_moving_session_date_uncompletes_original_mission`).
4. **Registro perto da meia-noite** → “hoje” é a data civil de São Paulo, não a UTC (Tarefa 1, `test_today_uses_sao_paulo_civil_date`).
5. **Bloco dispensado ou já concluído** → sessão em bloco dispensado retorna 422 `occurrence_skipped`; remanejar bloco concluído retorna 422 `not_pending` (Tarefa 8, `test_skipped_block_rejects_session_and_completed_block_cannot_move`).

## Mapa de arquivos

```text
.env.example · .dockerignore · Dockerfile · docker-compose.yml
ops/db-init/01-test-db.sql            # cria cgu_test na primeira inicialização do volume
ops/backup.sh                         # pg_dump diário, 14 cópias
scripts/restore-check.sh              # restaura um dump em database temporária e mostra contagens
scripts/make_icons.py                 # gera PNGs do PWA sem dependências
apps/api/
  pyproject.toml · uv.lock · alembic.ini
  migrations/{env.py,script.py.mako,versions/}
  app/config.py db.py clock.py errors.py main.py models.py seed.py
  app/domain/{cycle,weeks,xp,streak,mission}.py      # funções puras
  app/catalog/router.py                              # edital, progresso, settings
  app/planning/{service,router}.py                   # plano, semanas, ocorrências
  app/study/{service,router}.py                      # sessões
  app/game/config.py                                 # lê gamificacao.json
  app/game/snapshot.py                               # fatos → XP, nível, sequência; tracked(); game_delta
  app/game/router.py                                 # resumo, extrato, folgas
  app/game/missions.py · mission_router.py           # missão do dia e visão do dia
  tests/conftest.py · tests/unit/* · tests/integration/*
apps/web/
  index.html · vite.config.ts · public/{manifest.webmanifest,icons/}
  src/main.tsx · index.css · test/setup.ts
  src/app/{App,Hud}.tsx
  src/shared/api/{client,types,hooks}.ts · shared/format.ts · shared/ui/GameToast.tsx
  src/features/today/{TodayPage,SessionForm,MissionRing}.tsx
  src/features/{cycle/CyclePage,catalog/CatalogPage,settings/SettingsPage}.tsx
```

Pegadinhas já encontradas no protótipo, que este plano evita:

- `window` é palavra reservada no Postgres: a CHECK escrita à mão precisa de `"window"` entre aspas.
- O Alembic só importa `app` com `prepend_sys_path = .` no `alembic.ini`.
- Testes unitários e de integração com o mesmo nome de arquivo (`test_mission.py`) colidem sem `__init__.py` nas pastas de teste.
- O template do Vite liga `erasableSyntaxOnly` e `verbatimModuleSyntax`: nada de *parameter properties* em classes, e tipos são importados com `import type`.
- Sem `globals: true`, o Testing Library não limpa o DOM entre testes: `cleanup()` vai no `setup.ts`.
- Caminhos de dados nos testes usam `config.DATA_DIR`, nunca `Path(__file__).parents[n]`, para funcionar no Mac e no container.

---

### Task 1: Esqueleto da API (sem banco)

**Files:**
- Create: `apps/api/pyproject.toml`, `apps/api/app/__init__.py`, `apps/api/app/{config,db,clock,errors,main}.py`
- Test: `apps/api/tests/__init__.py`, `apps/api/tests/conftest.py`, `apps/api/tests/unit/__init__.py`, `apps/api/tests/unit/test_app_shell.py`, `apps/api/tests/unit/test_clock.py`

**Interfaces:**
- Produces: `app.config.{DATABASE_URL, ALLOWED_HOSTS, STATIC_DIR, DATA_DIR, host_allowed(host) -> bool}`; `app.db.{Base, engine, SessionLocal, get_db}`; `app.clock.get_today() -> date`; `app.errors.ApiError(status, code, message, fields=None)` e `install(app)`; `app.main.create_app()`, `app.main.app`.

- [ ] **Step 1: Criar o projeto Python e as dependências**

```bash
mkdir -p apps/api/app apps/api/tests/unit apps/api/tests/integration
cd apps/api
```

```toml
[project]
name = "cgu-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

```bash
uv python pin 3.12
uv add fastapi 'uvicorn[standard]' sqlalchemy 'psycopg[binary]' alembic pydantic tzdata
uv add --dev pytest httpx
touch app/__init__.py tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py
```

Expected: `uv.lock` criado; `pyproject.toml` com as dependências listadas.

- [ ] **Step 2: Escrever os testes que falham**

`apps/api/tests/conftest.py`:

```python
import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://cgu:cgu@localhost:5432/cgu_test")
os.environ.setdefault("ALLOWED_HOSTS", "127.0.0.1,localhost,testserver,*.ts.net")
```

`apps/api/tests/unit/test_app_shell.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers["x-request-id"]


def test_mutation_requires_json():
    r = client.post("/api/v1/health", content="x", headers={"content-type": "text/plain"})
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "unsupported_media_type"


def test_foreign_origin_is_rejected():
    r = client.post("/api/v1/health", json={}, headers={"origin": "https://evil.example"})
    assert r.status_code == 403


def test_tailnet_origin_is_allowed_past_guard():
    r = client.post("/api/v1/health", json={}, headers={"origin": "https://mac.tail1234.ts.net"})
    assert r.status_code == 405


def test_unknown_host_is_rejected():
    r = client.get("/api/v1/health", headers={"host": "attacker.example"})
    assert r.status_code == 400
```

`apps/api/tests/unit/test_clock.py`:

```python
from datetime import date, datetime, timezone

from app import clock


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 10, 2, 30, tzinfo=timezone.utc).astimezone(tz)


def test_today_uses_sao_paulo_civil_date(monkeypatch):
    monkeypatch.setattr(clock, "datetime", FrozenDatetime)
    assert clock.get_today() == date(2026, 10, 9)
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `cd apps/api && uv run pytest tests/unit -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 4: Implementar config, db, clock e errors**

`apps/api/app/config.py`:

```python
import os
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://cgu:cgu@localhost:5432/cgu")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]
STATIC_DIR = Path(os.environ.get("STATIC_DIR", API_DIR.parent / "web" / "dist"))
DATA_DIR = Path(os.environ.get("DATA_DIR", API_DIR.parent.parent / "docs" / "data"))


def host_allowed(host: str | None) -> bool:
    if not host:
        return False
    for allowed in ALLOWED_HOSTS:
        if allowed == "*" or host == allowed or (allowed.startswith("*.") and host.endswith(allowed[1:])):
            return True
    return False
```

`apps/api/app/db.py`:

```python
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app import config


class Base(DeclarativeBase):
    pass


engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db
```

`apps/api/app/clock.py`:

```python
from datetime import date, datetime
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("America/Sao_Paulo")


def get_today() -> date:
    """Dependência FastAPI; os testes a substituem por uma data fixa."""
    return datetime.now(TIMEZONE).date()
```

`apps/api/app/errors.py`:

```python
import logging
import uuid
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import config

log = logging.getLogger("app")
MUTATIONS = {"POST", "PUT", "PATCH", "DELETE"}
WITH_BODY = {"POST", "PUT", "PATCH"}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, fields: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.fields = status, code, message, fields or {}


def _body(request_id: str, code: str, message: str, fields: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id, "fields": fields or {}}}


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def guard(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex
        rid = request.state.request_id
        if request.url.path.startswith("/api/") and request.method in MUTATIONS:
            origin = request.headers.get("origin")
            if origin and not config.host_allowed(urlsplit(origin).hostname):
                return JSONResponse(_body(rid, "forbidden_origin", "Origem não permitida."), status_code=403)
            ctype = request.headers.get("content-type", "")
            if request.method in WITH_BODY and not ctype.startswith("application/json"):
                return JSONResponse(_body(rid, "unsupported_media_type", "Envie JSON."), status_code=415)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        return JSONResponse(_body(_rid(request), exc.code, exc.message, exc.fields), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        fields = {".".join(str(p) for p in e["loc"][1:]) or "body": e["msg"] for e in exc.errors()}
        return JSONResponse(_body(_rid(request), "invalid_input", "Revise os campos destacados.", fields), status_code=422)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        log.exception("erro inesperado request_id=%s", _rid(request))
        return JSONResponse(_body(_rid(request), "internal_error", "Erro interno. Tente novamente."), status_code=500)
```

- [ ] **Step 5: Implementar `main.py` (sem roteadores de domínio ainda)**

```python
from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import config, errors


def mount_spa(app: FastAPI) -> None:
    static = config.STATIC_DIR.resolve()
    if not (static / "index.html").is_file():
        return

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise errors.ApiError(404, "not_found", "Rota inexistente.")
        candidate = (static / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(static):
            return FileResponse(candidate)
        return FileResponse(static / "index.html")


def create_app() -> FastAPI:
    app = FastAPI(title="CGU 2026", docs_url="/api/docs", openapi_url="/api/openapi.json")
    errors.install(app)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.ALLOWED_HOSTS)
    api = APIRouter(prefix="/api/v1")

    @api.get("/health")
    def health():
        return {"status": "ok"}

    for router in ():  # cada tarefa seguinte registra seu roteador aqui
        api.include_router(router)
    app.include_router(api)
    mount_spa(app)
    return app


app = create_app()
```

- [ ] **Step 6: Rodar e ver passar**

Run: `cd apps/api && uv run pytest tests/unit -q`
Expected: 6 passed.

- [ ] **Step 7: Commit**

```bash
git add apps/api
git commit -m "feat(api): esqueleto FastAPI com guarda de Host/Origin/JSON e erros padronizados"
```

---

### Task 2: Domínio — geração de semanas do ciclo

**Files:**
- Create: `apps/api/app/domain/__init__.py`, `apps/api/app/domain/cycle.py`
- Test: `apps/api/tests/unit/test_cycle.py`

**Interfaces:**
- Consumes: `app.config.DATA_DIR` (lê `docs/data/ciclo-inicial.json` no teste).
- Produces: `SlotInput(code, weekday, window, minutes, purpose)`, `TemplateInput(effective_from, slots)`, `OccurrenceInput(cycle_slot_code, week_start, planned_on, window, status="pending")`, `CycleError`, `week_start_of(day) -> date`, `select_template(templates, week_start) -> TemplateInput`, `generate_week(template, week_start, plan_starts_on, plan_ends_on) -> list[OccurrenceInput]`, `week_index(week_start, plan_starts_on) -> int`, `suggest_topic(selection_mode, candidates, index) -> str | None`, `WINDOW_ORDER`.

- [ ] **Step 1: Escrever o teste que falha**

`apps/api/tests/unit/test_cycle.py`:

```python
import json
from collections import Counter
from datetime import date

import pytest

from app import config
from app.domain.cycle import (
    CycleError,
    SlotInput,
    TemplateInput,
    generate_week,
    select_template,
    suggest_topic,
    week_index,
    week_start_of,
)

DATA = config.DATA_DIR / "ciclo-inicial.json"
PLAN_START, PLAN_END = date(2026, 10, 9), date(2026, 12, 11)


def initial_template() -> TemplateInput:
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    slots = tuple(
        SlotInput(s["code"], s["weekday"], s["window"], s["minutes"], s["purpose"]) for s in raw["slots"]
    )
    return TemplateInput(date.fromisoformat(raw["template"]["effective_from"]), slots)


def test_partial_first_week_has_only_friday_blocks():
    occ = generate_week(initial_template(), date(2026, 10, 5), PLAN_START, PLAN_END)
    assert [o.cycle_slot_code for o in occ] == ["S13", "S14", "S15"]
    assert {o.planned_on for o in occ} == {date(2026, 10, 9)}
    assert [o.window for o in occ] == ["before", "middle", "after"]


def test_full_week_has_15_blocks_and_purpose_split():
    tpl = initial_template()
    occ = generate_week(tpl, date(2026, 10, 12), PLAN_START, PLAN_END)
    assert len(occ) == 15
    assert min(o.planned_on for o in occ) == date(2026, 10, 12)
    assert max(o.planned_on for o in occ) == date(2026, 10, 16)
    by_code = {s.code: s for s in tpl.slots}
    minutes = Counter()
    for o in occ:
        minutes[by_code[o.cycle_slot_code].purpose] += by_code[o.cycle_slot_code].minutes
    assert minutes == {"specific": 420, "basic": 180, "complementary": 180, "essay": 120}


def test_last_week_ends_on_plan_end():
    occ = generate_week(initial_template(), date(2026, 12, 7), PLAN_START, PLAN_END)
    assert len(occ) == 15
    assert max(o.planned_on for o in occ) == date(2026, 12, 11)


@pytest.mark.parametrize(
    ("week_start", "message"),
    [(date(2026, 10, 13), "segunda-feira"), (date(2026, 12, 14), "fora do período")],
)
def test_invalid_weeks(week_start, message):
    with pytest.raises(CycleError, match=message):
        generate_week(initial_template(), week_start, PLAN_START, PLAN_END)


def test_select_template_ignores_future_templates():
    old = TemplateInput(date(2026, 10, 5), ())
    new = TemplateInput(date(2026, 10, 26), ())
    assert select_template([old, new], date(2026, 10, 19)) is old
    assert select_template([old, new], date(2026, 10, 26)) is new
    with pytest.raises(CycleError):
        select_template([new], date(2026, 10, 19))


def test_week_helpers_and_topic_suggestion():
    assert week_start_of(date(2026, 10, 9)) == date(2026, 10, 5)
    assert week_index(date(2026, 10, 5), PLAN_START) == 0
    assert week_index(date(2026, 10, 12), PLAN_START) == 1
    assert suggest_topic("alternate_subjects", ["B01.01", "B02.01"], 1) == "B01.01"
    assert suggest_topic("alternate_subjects", ["B01.01", "B02.01"], 2) == "B02.01"
    assert suggest_topic("rotate_subjects", ["B01.01", "B02.01", "B03.01", "B04.01"], 3) == "B03.01"
    s12 = ["E04.01", "E04.02", "E01.04", "E02.04"]
    assert suggest_topic("alternate_delivery_and_interfaces_ai", s12, 1) == "E04.01"
    assert suggest_topic("alternate_delivery_and_interfaces_ai", s12, 2) == "E01.04"
    assert suggest_topic("choose_topic", ["E01.02", "E01.03"], 5) == "E01.02"
    assert suggest_topic("technical_case", [], 1) is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd apps/api && touch app/domain/__init__.py && uv run pytest tests/unit/test_cycle.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.domain.cycle'`.

- [ ] **Step 3: Implementar**

`apps/api/app/domain/cycle.py`:

```python
"""Geração de semanas do ciclo (R02). Funções puras, sem banco."""

from dataclasses import dataclass
from datetime import date, timedelta

WINDOW_ORDER = {"before": 0, "middle": 1, "after": 2}
ROTATING_MODES = {"alternate_subjects", "rotate_subjects"}


class CycleError(ValueError):
    pass


@dataclass(frozen=True)
class SlotInput:
    code: str
    weekday: int  # 1 = segunda … 5 = sexta
    window: str
    minutes: int
    purpose: str


@dataclass(frozen=True)
class TemplateInput:
    effective_from: date
    slots: tuple[SlotInput, ...]


@dataclass(frozen=True)
class OccurrenceInput:
    cycle_slot_code: str
    week_start: date
    planned_on: date
    window: str
    status: str = "pending"


def week_start_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def select_template(templates: list[TemplateInput], week_start: date) -> TemplateInput:
    valid = [t for t in templates if t.effective_from <= week_start]
    if not valid:
        raise CycleError("Nenhum template vigente para esta semana.")
    return max(valid, key=lambda t: t.effective_from)


def generate_week(
    template: TemplateInput, week_start: date, plan_starts_on: date, plan_ends_on: date
) -> list[OccurrenceInput]:
    if week_start.weekday() != 0:
        raise CycleError("A semana deve começar numa segunda-feira.")
    if week_start + timedelta(days=6) < plan_starts_on or week_start > plan_ends_on:
        raise CycleError("Semana fora do período do plano.")
    if template.effective_from > week_start:
        raise CycleError("Template ainda não vigente nesta semana.")
    slots = sorted(template.slots, key=lambda s: (s.weekday, WINDOW_ORDER[s.window]))
    result = []
    for slot in slots:
        planned_on = week_start + timedelta(days=slot.weekday - 1)
        if plan_starts_on <= planned_on <= plan_ends_on:
            result.append(OccurrenceInput(slot.code, week_start, planned_on, slot.window))
    return result


def week_index(week_start: date, plan_starts_on: date) -> int:
    """0 = semana que contém o início do plano (parcial); 1 = primeira semana cheia."""
    return (week_start - week_start_of(plan_starts_on)).days // 7


def suggest_topic(selection_mode: str, candidates: list[str], index: int) -> str | None:
    """Semanas ímpares usam o primeiro candidato; pares, o segundo (02 §3)."""
    if not candidates:
        return None
    if selection_mode in ROTATING_MODES:
        return candidates[(index - 1) % len(candidates)]
    if selection_mode == "alternate_delivery_and_interfaces_ai":
        delivery = [c for c in candidates if c.startswith("E04")]
        interfaces = [c for c in candidates if not c.startswith("E04")]
        group = delivery if index % 2 == 1 else interfaces
        return (group or candidates)[0]
    return candidates[0]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd apps/api && uv run pytest tests/unit/test_cycle.py -q`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/domain apps/api/tests/unit/test_cycle.py
git commit -m "feat(domain): geração de semanas com semana inicial parcial e sugestão de tópico"
```

---

### Task 3: Domínio — XP, nível e semana completa

**Files:**
- Create: `apps/api/app/domain/xp.py`, `apps/api/app/domain/weeks.py`
- Test: `apps/api/tests/unit/test_xp.py`

**Interfaces:**
- Produces: `XpTable(...)` (padrões = `gamificacao.json`), `SessionFact(id, studied_on, minutes)`, `BlockFact(occurrence_id, completed_on)`, `MissionFact(mission_id, mission_date, complete, optional_done)`, `GameFacts(sessions, blocks, missions, complete_week_starts)`, `XpEntry(date, source, ref_id, xp)`, `TitleBand(first, last, title)`, `LevelInfo(level, title, xp_total, xp_into_level, xp_for_next)`, `xp_ledger(facts, table) -> list[XpEntry]`, `cumulative_xp(level) -> int`, `level_for_xp(total, titles=DEFAULT_TITLES) -> LevelInfo`; `weeks.minutes_goal_for_week(week_start, plan_starts_on, generated_minutes, default_goal) -> int`, `weeks.is_week_complete(occurrence_statuses, actual_minutes, minutes_goal) -> bool`. Fontes do extrato: `session_minutes`, `weekend_day`, `block_completed`, `mission_complete`, `mission_optional`, `week_complete`.

- [ ] **Step 1: Escrever o teste que falha**

`apps/api/tests/unit/test_xp.py`:

```python
from datetime import date

import pytest

from app.domain.weeks import is_week_complete, minutes_goal_for_week
from app.domain.xp import (
    BlockFact,
    GameFacts,
    MissionFact,
    SessionFact,
    XpTable,
    level_for_xp,
    xp_ledger,
)

FRI, SAT = date(2026, 10, 9), date(2026, 10, 10)
T = XpTable()


def total(facts: GameFacts) -> int:
    return sum(e.xp for e in xp_ledger(facts, T))


def test_session_block_and_mission_same_day():
    facts = GameFacts(
        sessions=(SessionFact("s1", FRI, 50),),
        blocks=(BlockFact("o1", FRI),),
        missions=(MissionFact("m1", FRI, complete=True, optional_done=0),),
    )
    assert total(facts) == 120


def test_daily_minutes_cap():
    facts = GameFacts(sessions=(SessionFact("a", FRI, 200), SessionFact("b", FRI, 100)))
    assert total(facts) == 240


def test_no_records_no_xp():
    assert xp_ledger(GameFacts(), T) == []


def test_optional_items_and_weekend_bonus():
    facts = GameFacts(
        sessions=(SessionFact("s", SAT, 45),),
        missions=(MissionFact("m", SAT, complete=False, optional_done=1),),
    )
    assert total(facts) == 45 + 20 + 10


def test_weekend_below_minimum_has_no_bonus():
    assert total(GameFacts(sessions=(SessionFact("s", SAT, 29),))) == 29


def test_week_complete_dated_on_sunday():
    entries = xp_ledger(GameFacts(complete_week_starts=frozenset({date(2026, 10, 12)})), T)
    assert [(e.date, e.source, e.xp) for e in entries] == [(date(2026, 10, 18), "week_complete", 150)]


@pytest.mark.parametrize(
    ("xp", "level", "title"),
    [(0, 1, "Estagiário"), (99, 1, "Estagiário"), (100, 2, "Estagiário"), (300, 3, "Estagiário"),
     (600, 4, "Analista"), (15300, 18, "AFFC")],
)
def test_levels(xp, level, title):
    info = level_for_xp(xp)
    assert (info.level, info.title) == (level, title)


def test_level_progress_fields():
    info = level_for_xp(150)
    assert (info.level, info.xp_into_level, info.xp_for_next) == (2, 50, 200)


def test_week_completion_rules():
    assert minutes_goal_for_week(date(2026, 10, 5), date(2026, 10, 9), 180, 900) == 180
    assert minutes_goal_for_week(date(2026, 10, 12), date(2026, 10, 9), 900, 900) == 900
    assert is_week_complete(["completed"] * 3, 0, 180)
    assert not is_week_complete(["completed", "skipped"], 100, 900)
    assert is_week_complete(["completed", "skipped"], 900, 900)
    assert not is_week_complete([], 0, 0)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd apps/api && uv run pytest tests/unit/test_xp.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.domain.weeks'`.

- [ ] **Step 3: Implementar**

`apps/api/app/domain/weeks.py`:

```python
"""Semana completa e meta de minutos da semana ([10] §3 e §6)."""

from datetime import date


def minutes_goal_for_week(
    week_start: date, plan_starts_on: date, generated_minutes: int, default_goal: int
) -> int:
    """Semana inicial parcial usa a soma dos blocos gerados; as demais, a meta configurada."""
    return generated_minutes if week_start < plan_starts_on else default_goal


def is_week_complete(occurrence_statuses: list[str], actual_minutes: int, minutes_goal: int) -> bool:
    if occurrence_statuses and all(s == "completed" for s in occurrence_statuses):
        return True
    return minutes_goal > 0 and actual_minutes >= minutes_goal
```

`apps/api/app/domain/xp.py`:

```python
"""Extrato de XP e nível ([10] §3–4). Tudo derivado dos registros."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass(frozen=True)
class XpTable:
    per_session_minute: int = 1
    session_minutes_daily_cap: int = 240
    block_completed: int = 20
    mission_complete: int = 50
    mission_optional_item: int = 10
    week_complete: int = 150
    weekend_active_day: int = 20
    weekend_min_minutes: int = 30


@dataclass(frozen=True)
class SessionFact:
    id: str
    studied_on: date
    minutes: int


@dataclass(frozen=True)
class BlockFact:
    occurrence_id: str
    completed_on: date


@dataclass(frozen=True)
class MissionFact:
    mission_id: str
    mission_date: date
    complete: bool
    optional_done: int


@dataclass(frozen=True)
class GameFacts:
    sessions: tuple[SessionFact, ...] = ()
    blocks: tuple[BlockFact, ...] = ()
    missions: tuple[MissionFact, ...] = ()
    complete_week_starts: frozenset[date] = field(default_factory=frozenset)


@dataclass(frozen=True)
class XpEntry:
    date: date
    source: str
    ref_id: str
    xp: int


@dataclass(frozen=True)
class TitleBand:
    first: int
    last: int | None
    title: str


@dataclass(frozen=True)
class LevelInfo:
    level: int
    title: str
    xp_total: int
    xp_into_level: int
    xp_for_next: int


DEFAULT_TITLES = (
    TitleBand(1, 3, "Estagiário"),
    TitleBand(4, 7, "Analista"),
    TitleBand(8, 12, "Auditor Júnior"),
    TitleBand(13, 17, "Auditor"),
    TitleBand(18, None, "AFFC"),
)


def xp_ledger(facts: GameFacts, table: XpTable) -> list[XpEntry]:
    entries: list[XpEntry] = []
    by_day: dict[date, list[SessionFact]] = defaultdict(list)
    for s in facts.sessions:
        by_day[s.studied_on].append(s)
    for day in sorted(by_day):
        remaining = table.session_minutes_daily_cap
        day_sessions = sorted(by_day[day], key=lambda s: s.id)
        for s in day_sessions:
            xp = min(s.minutes * table.per_session_minute, remaining)
            remaining -= xp
            if xp > 0:
                entries.append(XpEntry(day, "session_minutes", s.id, xp))
        total_minutes = sum(s.minutes for s in day_sessions)
        if day.weekday() >= 5 and total_minutes >= table.weekend_min_minutes:
            entries.append(XpEntry(day, "weekend_day", day.isoformat(), table.weekend_active_day))
    for b in facts.blocks:
        entries.append(XpEntry(b.completed_on, "block_completed", b.occurrence_id, table.block_completed))
    for m in facts.missions:
        if m.complete:
            entries.append(XpEntry(m.mission_date, "mission_complete", m.mission_id, table.mission_complete))
        if m.optional_done:
            entries.append(
                XpEntry(m.mission_date, "mission_optional", m.mission_id, m.optional_done * table.mission_optional_item)
            )
    for ws in facts.complete_week_starts:
        entries.append(XpEntry(ws + timedelta(days=6), "week_complete", ws.isoformat(), table.week_complete))
    return sorted(entries, key=lambda e: (e.date, e.source, e.ref_id))


def cumulative_xp(level: int) -> int:
    return 50 * level * (level - 1)


def level_for_xp(total: int, titles: tuple[TitleBand, ...] = DEFAULT_TITLES) -> LevelInfo:
    level = 1
    while cumulative_xp(level + 1) <= total:
        level += 1
    title = next(t.title for t in titles if t.first <= level and (t.last is None or level <= t.last))
    return LevelInfo(level, title, total, total - cumulative_xp(level), 100 * level)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd apps/api && uv run pytest tests/unit/test_xp.py -q`
Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/domain/xp.py apps/api/app/domain/weeks.py apps/api/tests/unit/test_xp.py
git commit -m "feat(domain): extrato de XP com tetos, níveis e semana completa"
```

---

### Task 4: Domínio — sequência, folgas e congelamentos

**Files:**
- Create: `apps/api/app/domain/streak.py`
- Test: `apps/api/tests/unit/test_streak.py`

**Interfaces:**
- Produces: `StreakState(current, best, freezes_available, frozen_days, at_stake_today, minutes_today)`, `streak_state(minutes_by_date, day_offs, complete_week_starts, start, today, min_minutes=30, max_freezes=2) -> StreakState`.

- [ ] **Step 1: Escrever o teste que falha**

`apps/api/tests/unit/test_streak.py`:

```python
from datetime import date, timedelta

from app.domain.streak import streak_state

START = date(2026, 10, 9)


def d(month: int, day: int) -> date:
    return date(2026, month, day)


def test_streak_breaks_without_freeze():
    s = streak_state({d(10, 9): 45, d(10, 12): 30}, set(), set(), START, d(10, 14))
    assert (s.current, s.best, s.frozen_days) == (0, 2, ())


def test_day_off_is_neutral():
    s = streak_state({d(10, 9): 45, d(10, 12): 30}, {d(10, 13)}, set(), START, d(10, 14))
    assert s.current == 2
    assert s.at_stake_today is True


def test_weekend_never_breaks():
    s = streak_state({d(10, 9): 60}, set(), set(), START, d(10, 12))
    assert s.current == 1


def test_today_in_play_does_not_change_streak():
    s = streak_state({d(10, 9): 60, d(10, 12): 10}, set(), set(), START, d(10, 12))
    assert (s.current, s.at_stake_today, s.minutes_today) == (1, True, 10)


def test_today_reaching_minimum_counts():
    s = streak_state({d(10, 9): 60, d(10, 12): 30}, set(), set(), START, d(10, 12))
    assert (s.current, s.at_stake_today) == (2, False)


def test_complete_week_grants_freeze_that_covers_next_missed_day():
    minutes = {d(10, 12) + timedelta(days=i): 60 for i in range(5)}
    s = streak_state(minutes, set(), {d(10, 12)}, START, d(10, 20))
    assert s.current == 5
    assert s.frozen_days == (d(10, 19),)
    assert s.freezes_available == 0


def test_freezes_capped_at_two():
    weeks = {d(10, 12), d(10, 19), d(10, 26)}
    minutes = {}
    for ws in weeks:
        for i in range(5):
            minutes[ws + timedelta(days=i)] = 60
    s = streak_state(minutes, set(), weeks, START, d(11, 2))
    assert s.freezes_available == 2


def test_before_plan_start_nothing_counts():
    s = streak_state({}, set(), set(), START, d(10, 8))
    assert (s.current, s.at_stake_today) == (0, False)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd apps/api && uv run pytest tests/unit/test_streak.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.domain.streak'`.

- [ ] **Step 3: Implementar**

`apps/api/app/domain/streak.py`:

```python
"""Sequência de dias úteis com folgas e congelamentos ([10] §5)."""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class StreakState:
    current: int
    best: int
    freezes_available: int
    frozen_days: tuple[date, ...]
    at_stake_today: bool
    minutes_today: int


def streak_state(
    minutes_by_date: dict[date, int],
    day_offs: set[date],
    complete_week_starts: set[date],
    start: date,
    today: date,
    min_minutes: int = 30,
    max_freezes: int = 2,
) -> StreakState:
    current = best = freezes = 0
    frozen: list[date] = []
    day = start
    while day < today:
        if day.weekday() < 5 and day not in day_offs:
            if minutes_by_date.get(day, 0) >= min_minutes:
                current += 1
                best = max(best, current)
            elif freezes > 0:
                freezes -= 1
                frozen.append(day)
            else:
                current = 0
        if day.weekday() == 6 and day - timedelta(days=6) in complete_week_starts:
            freezes = min(max_freezes, freezes + 1)
        day += timedelta(days=1)

    minutes_today = minutes_by_date.get(today, 0)
    counts_today = today >= start and today.weekday() < 5 and today not in day_offs
    at_stake = False
    if counts_today and minutes_today >= min_minutes:
        current += 1
        best = max(best, current)
    elif counts_today:
        at_stake = True
    return StreakState(current, best, freezes, tuple(frozen), at_stake, minutes_today)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd apps/api && uv run pytest tests/unit/test_streak.py -q`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/domain/streak.py apps/api/tests/unit/test_streak.py
git commit -m "feat(domain): sequência em dias úteis com folgas e congelamentos"
```

---

### Task 5: Domínio — missão do dia

**Files:**
- Create: `apps/api/app/domain/mission.py`
- Test: `apps/api/tests/unit/test_mission.py`

**Interfaces:**
- Produces: `OccRef(id, status, planned_on, window)`, `MissionItemInput(position, kind, required, ref_id=None, target=None, na_reason=None)`, `DayFacts(mission_date, occurrence_status, occurrence_planned_on, occurrence_completed_on, question_items=0, checkout_saved=False)`, `ItemState(state, reason=None)`, `mission_kind(day) -> "weekday"|"free"`, `build_mission(day, occurrences, question_goal=0) -> list[MissionItemInput]`, `item_state(item, facts) -> ItemState`, `is_complete(states) -> bool`, `optional_done(states) -> int`. `states` é `list[tuple[bool, ItemState]]` (obrigatório, estado).

- [ ] **Step 1: Escrever o teste que falha**

`apps/api/tests/unit/test_mission.py`:

```python
from datetime import date

from app.domain.mission import (
    DayFacts,
    ItemState,
    MissionItemInput,
    OccRef,
    build_mission,
    is_complete,
    item_state,
    mission_kind,
    optional_done,
)

FRI = date(2026, 10, 9)


def occ(i: str, window: str, status: str = "pending") -> OccRef:
    return OccRef(i, status, FRI, window)


def test_weekday_mission_has_blocks_in_window_order_and_checkout():
    items = build_mission(FRI, [occ("c", "after"), occ("a", "before"), occ("b", "middle", "completed")])
    assert [(i.kind, i.ref_id, i.required) for i in items] == [
        ("block", "a", True), ("block", "b", True), ("block", "c", True), ("checkout", None, False),
    ]
    assert [i.position for i in items] == [0, 1, 2, 3]


def test_question_goal_adds_optional_item():
    items = build_mission(FRI, [], question_goal=20)
    assert [(i.kind, i.target, i.required) for i in items] == [("questions", 20, False), ("checkout", None, False)]


def test_kind():
    assert mission_kind(FRI) == "weekday"
    assert mission_kind(date(2026, 10, 10)) == "free"


def test_block_states():
    block = MissionItemInput(0, "block", True, ref_id="o1")
    base = {"occurrence_status": {"o1": "pending"}, "occurrence_planned_on": {"o1": FRI}}
    assert item_state(block, DayFacts(FRI, **base)).state == "pending"
    done = DayFacts(FRI, occurrence_status={"o1": "completed"}, occurrence_planned_on={"o1": FRI},
                    occurrence_completed_on={"o1": FRI})
    assert item_state(block, done).state == "done"
    late = DayFacts(FRI, occurrence_status={"o1": "completed"}, occurrence_planned_on={"o1": FRI},
                    occurrence_completed_on={"o1": date(2026, 10, 12)})
    assert item_state(block, late).state == "pending"
    moved = DayFacts(FRI, occurrence_status={"o1": "pending"}, occurrence_planned_on={"o1": date(2026, 10, 12)})
    assert item_state(block, moved) == ItemState("not_applicable", "rescheduled")
    skipped = DayFacts(FRI, occurrence_status={"o1": "skipped"}, occurrence_planned_on={"o1": FRI})
    assert item_state(block, skipped) == ItemState("not_applicable", "skipped")
    manual = MissionItemInput(0, "block", True, ref_id="o1", na_reason="Intermediário indisponível")
    assert item_state(manual, DayFacts(FRI, **base)).state == "not_applicable"


def test_checkout_and_questions_states():
    assert item_state(MissionItemInput(0, "checkout", False), DayFacts(FRI, checkout_saved=True)).state == "done"
    q = MissionItemInput(0, "questions", False, target=20)
    assert item_state(q, DayFacts(FRI, question_items=19)).state == "pending"
    assert item_state(q, DayFacts(FRI, question_items=20)).state == "done"


def test_completion_rules():
    done, na, pending = ItemState("done"), ItemState("not_applicable", "x"), ItemState("pending")
    assert not is_complete([(True, na), (True, na)])
    assert is_complete([(True, done), (True, na), (False, pending)])
    assert not is_complete([(True, done), (True, pending)])
    assert not is_complete([(False, done)])
    assert optional_done([(True, done), (False, done), (False, pending)]) == 1
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd apps/api && uv run pytest tests/unit/test_mission.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.domain.mission'`.

- [ ] **Step 3: Implementar**

`apps/api/app/domain/mission.py`:

```python
"""Missão do dia ([10] §2, R13)."""

from dataclasses import dataclass, field
from datetime import date

WINDOW_ORDER = {"before": 0, "middle": 1, "after": 2}


@dataclass(frozen=True)
class OccRef:
    id: str
    status: str
    planned_on: date
    window: str


@dataclass(frozen=True)
class MissionItemInput:
    position: int
    kind: str  # block | review | questions | checkout
    required: bool
    ref_id: str | None = None
    target: int | None = None
    na_reason: str | None = None


@dataclass(frozen=True)
class DayFacts:
    mission_date: date
    occurrence_status: dict[str, str] = field(default_factory=dict)
    occurrence_planned_on: dict[str, date] = field(default_factory=dict)
    occurrence_completed_on: dict[str, date] = field(default_factory=dict)
    question_items: int = 0
    checkout_saved: bool = False


@dataclass(frozen=True)
class ItemState:
    state: str  # pending | done | not_applicable
    reason: str | None = None


def mission_kind(day: date) -> str:
    return "free" if day.weekday() >= 5 else "weekday"


def build_mission(day: date, occurrences: list[OccRef], question_goal: int = 0) -> list[MissionItemInput]:
    items: list[MissionItemInput] = []
    for occ in sorted(occurrences, key=lambda o: WINDOW_ORDER[o.window]):
        items.append(MissionItemInput(len(items), "block", True, ref_id=occ.id))
    if question_goal > 0:
        items.append(MissionItemInput(len(items), "questions", False, target=question_goal))
    items.append(MissionItemInput(len(items), "checkout", False))
    return items


def item_state(item: MissionItemInput, facts: DayFacts) -> ItemState:
    if item.na_reason:
        return ItemState("not_applicable", item.na_reason)
    if item.kind == "block":
        completed_on = facts.occurrence_completed_on.get(item.ref_id)
        if completed_on is not None and completed_on <= facts.mission_date:
            return ItemState("done")
        if facts.occurrence_status.get(item.ref_id) == "skipped":
            return ItemState("not_applicable", "skipped")
        if facts.occurrence_planned_on.get(item.ref_id) != facts.mission_date:
            return ItemState("not_applicable", "rescheduled")
        return ItemState("pending")
    if item.kind == "questions":
        return ItemState("done" if facts.question_items >= (item.target or 0) else "pending")
    if item.kind == "checkout":
        return ItemState("done" if facts.checkout_saved else "pending")
    return ItemState("pending")


def is_complete(states: list[tuple[bool, ItemState]]) -> bool:
    required = [s.state for req, s in states if req]
    return (
        bool(required)
        and all(s in ("done", "not_applicable") for s in required)
        and any(s == "done" for s in required)
    )


def optional_done(states: list[tuple[bool, ItemState]]) -> int:
    return sum(1 for req, s in states if not req and s.state == "done")
```

- [ ] **Step 4: Rodar toda a suíte unitária**

Run: `cd apps/api && uv run pytest tests/unit -q`
Expected: 41 passed (6 + 7 + 14 + 8 + 6).

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/domain/mission.py apps/api/tests/unit/test_mission.py
git commit -m "feat(domain): missão do dia com itens congelados e conclusão derivada"
```

---

### Task 6: Persistência — compose, modelos, migração e seed

**Files:**
- Create: `.env.example`, `.dockerignore`, `Dockerfile`, `docker-compose.yml`, `ops/db-init/01-test-db.sql`
- Create: `apps/api/app/models.py`, `apps/api/app/seed.py`, `apps/api/alembic.ini`, `apps/api/migrations/{env.py,script.py.mako}`, `apps/api/migrations/versions/<gerado>_f1_schema.py`
- Test: `apps/api/tests/integration/conftest.py`, `apps/api/tests/integration/test_seed.py`

**Interfaces:**
- Consumes: `app.db.Base`, `app.config.DATA_DIR`.
- Produces: modelos `ExamVersion, Subject, Topic, TopicProgress, AppSettings, StudyPlan, CycleTemplate, CycleSlot, Occurrence, SessionTopic, StudySession (topic_ids property), DailyMission, MissionItem, DayOff`; `app.seed.seed(db)`, `app.seed.stable_id(*parts)`; fixtures `db`, `clock` (`clock.today` mutável, padrão 2026-10-09) e `client`; serviço compose `test` (perfil `test`) que roda pytest contra `cgu_test`.

- [ ] **Step 1: Arquivos de infraestrutura**

`.env.example`:

```text
# Copie para .env e troque a senha. O .env nunca vai para o Git.
POSTGRES_PASSWORD=troque-esta-senha
# Hosts aceitos (Host e Origin). Acrescente o nome *.ts.net do Mac ao ativar o tailscale serve.
ALLOWED_HOSTS=127.0.0.1,localhost
# Pasta dos backups diários; aponte para uma pasta sincronizada (ex.: iCloud Drive) para ter cópia fora do disco.
BACKUP_DIR=./backups
```

`.dockerignore`:

```text
**/node_modules
**/dist
**/.venv
**/__pycache__
backups
.env
```

`ops/db-init/01-test-db.sql`:

```sql
CREATE DATABASE cgu_test;
```

`Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1
FROM node:24-alpine AS web
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM python:3.12-slim AS base
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/docs/data
RUN pip install --no-cache-dir uv
WORKDIR /app/apps/api
COPY apps/api/pyproject.toml apps/api/uv.lock ./

FROM base AS dev
RUN uv sync --frozen --no-install-project
COPY apps/api/ ./
COPY docs/data /app/docs/data

FROM base AS runtime
RUN uv sync --frozen --no-install-project --no-dev
COPY apps/api/ ./
COPY docs/data /app/docs/data
COPY --from=web /web/dist /app/static
ENV STATIC_DIR=/app/static
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
```

`docker-compose.yml`:

```yaml
name: cgu2026

services:
  db:
    image: postgres:17.6
    environment:
      POSTGRES_DB: cgu
      POSTGRES_USER: cgu
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?defina POSTGRES_PASSWORD no .env}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./ops/db-init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cgu -d cgu"]
      interval: 5s
      timeout: 3s
      retries: 20
    restart: unless-stopped

  app:
    build: { context: ., target: runtime }
    environment:
      DATABASE_URL: postgresql+psycopg://cgu:${POSTGRES_PASSWORD}@db:5432/cgu
      ALLOWED_HOSTS: ${ALLOWED_HOSTS:-127.0.0.1,localhost}
    ports:
      - "127.0.0.1:8080:8000"
    depends_on:
      db: { condition: service_healthy }
    restart: unless-stopped

  backup:
    image: postgres:17.6
    environment:
      PGHOST: db
      PGUSER: cgu
      PGDATABASE: cgu
      PGPASSWORD: ${POSTGRES_PASSWORD}
      TZ: America/Sao_Paulo
    volumes:
      - ./ops/backup.sh:/backup.sh:ro
      - ${BACKUP_DIR:-./backups}:/backups
    entrypoint: ["sh", "/backup.sh"]
    depends_on:
      db: { condition: service_healthy }
    restart: unless-stopped

  test:
    profiles: [test]
    build: { context: ., target: dev }
    environment:
      DATABASE_URL: postgresql+psycopg://cgu:${POSTGRES_PASSWORD}@db:5432/cgu_test
      ALLOWED_HOSTS: 127.0.0.1,localhost,testserver,*.ts.net
    volumes:
      - ./apps/api:/app/apps/api
      - ./docs/data:/app/docs/data:ro
    command: ["pytest", "-q", "-p", "no:cacheprovider"]
    depends_on:
      db: { condition: service_healthy }

volumes:
  pgdata:
```

```bash
cp .env.example .env   # trocar POSTGRES_PASSWORD por uma senha local
```

Os serviços `app` e `backup` só sobem na Tarefa 13. Antes disso, apenas `db` e `test` são usados.

- [ ] **Step 2: Escrever os testes de integração que falham**

`apps/api/tests/integration/conftest.py`:

```python
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import models  # noqa: F401  (registra as tabelas)
from app.clock import get_today
from app.db import Base, SessionLocal, engine
from app.main import app
from app.seed import seed

FRIDAY = date(2026, 10, 9)


@pytest.fixture(scope="session", autouse=True)
def schema():
    assert engine.url.database.endswith("_test"), "testes de integração só rodam em database *_test"
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def db():
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    with SessionLocal() as session:
        seed(session)
        yield session


class Clock:
    def __init__(self, today: date):
        self.today = today


@pytest.fixture
def clock():
    return Clock(FRIDAY)


@pytest.fixture
def client(db, clock):
    app.dependency_overrides[get_today] = lambda: clock.today
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

`apps/api/tests/integration/test_seed.py`:

```python
from sqlalchemy import func, select

from app.models import AppSettings, CycleSlot, CycleTemplate, StudyPlan, Subject, Topic
from app.seed import seed


def counts(db):
    return {
        "subjects": db.scalar(select(func.count()).select_from(Subject)),
        "topics": db.scalar(select(func.count()).select_from(Topic)),
        "plans": db.scalar(select(func.count()).select_from(StudyPlan)),
        "templates": db.scalar(select(func.count()).select_from(CycleTemplate)),
        "slots": db.scalar(select(func.count()).select_from(CycleSlot)),
        "minutes": db.scalar(select(func.sum(CycleSlot.minutes))),
    }


def test_seed_is_idempotent(db):
    expected = {"subjects": 13, "topics": 68, "plans": 1, "templates": 1, "slots": 15, "minutes": 900}
    assert counts(db) == expected
    seed(db)
    assert counts(db) == expected


def test_seed_never_overwrites_settings(db):
    settings = db.get(AppSettings, 1)
    settings.streak_min_minutes = 45
    db.commit()
    seed(db)
    db.expire_all()
    assert db.get(AppSettings, 1).streak_min_minutes == 45
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `docker compose --profile test run --rm --build test pytest tests/integration/test_seed.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.models'`.

- [ ] **Step 4: Implementar os modelos**

`apps/api/app/models.py`:

```python
"""Modelos ORM da F1. Valores derivados (XP, sequência, conclusão de missão) não têm coluna."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

WINDOWS = "'before','middle','after'"


class Versioned:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class ExamVersion(Base):
    __tablename__ = "exam_versions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    exam_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text)
    publication_date: Mapped[date] = mapped_column(Date)
    source_url: Mapped[str] = mapped_column(Text)
    source_sha256: Mapped[str] = mapped_column(String(64))
    exam_date: Mapped[date] = mapped_column(Date)
    scoring_rules: Mapped[dict] = mapped_column(JSONB)


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    exam_version_id: Mapped[str] = mapped_column(ForeignKey("exam_versions.id"))
    paper: Mapped[str] = mapped_column(String(2))
    title: Mapped[str] = mapped_column(Text)
    source_ref: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    topics: Mapped[list["Topic"]] = relationship(order_by="Topic.position")


class Topic(Base):
    __tablename__ = "topics"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"))
    title: Mapped[str] = mapped_column(Text)
    source_ref: Mapped[str] = mapped_column(Text)
    is_summary: Mapped[bool] = mapped_column(Boolean)
    position: Mapped[int] = mapped_column(Integer)


class TopicProgress(Versioned, Base):
    __tablename__ = "topic_progress"
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(16))
    declared_on: Mapped[date] = mapped_column(Date)
    __table_args__ = (
        CheckConstraint(
            "status in ('not_started','in_progress','first_pass','reviewed')", name="ck_topic_progress_status"
        ),
    )


class AppSettings(Versioned, Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timezone: Mapped[str] = mapped_column(String(64))
    weekly_goals: Mapped[dict] = mapped_column(JSONB)
    daily_question_goal: Mapped[int] = mapped_column(Integer)
    streak_min_minutes: Mapped[int] = mapped_column(Integer)
    max_freezes: Mapped[int] = mapped_column(Integer)
    __table_args__ = (CheckConstraint("id = 1", name="ck_settings_singleton"),)


class StudyPlan(Base):
    __tablename__ = "study_plans"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    exam_version_id: Mapped[str] = mapped_column(ForeignKey("exam_versions.id"))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    exam_version: Mapped[ExamVersion] = relationship()


class CycleTemplate(Base):
    __tablename__ = "cycle_templates"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    study_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("study_plans.id"))
    effective_from: Mapped[date] = mapped_column(Date)
    weekly_minutes: Mapped[int] = mapped_column(Integer)
    origin: Mapped[str] = mapped_column(String(16))
    slots: Mapped[list["CycleSlot"]] = relationship(order_by="CycleSlot.position", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("study_plan_id", "effective_from", name="uq_template_plan_effective"),)


class CycleSlot(Base):
    __tablename__ = "cycle_slots"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    cycle_template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cycle_templates.id"))
    code: Mapped[str] = mapped_column(String(8))
    weekday: Mapped[int] = mapped_column(Integer)
    window: Mapped[str] = mapped_column(String(8))
    minutes: Mapped[int] = mapped_column(Integer)
    purpose: Mapped[str] = mapped_column(String(16))
    activity: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(Text)
    selection_mode: Mapped[str] = mapped_column(String(48))
    candidate_topic_ids: Mapped[list[str]] = mapped_column(JSONB)
    position: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("cycle_template_id", "code", name="uq_slot_template_code"),)


class Occurrence(Versioned, Base):
    __tablename__ = "occurrences"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cycle_slot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cycle_slots.id"))
    week_start: Mapped[date] = mapped_column(Date)
    planned_on: Mapped[date] = mapped_column(Date, index=True)
    window: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    skip_reason: Mapped[str | None] = mapped_column(Text)
    slot: Mapped[CycleSlot] = relationship(lazy="joined")
    __table_args__ = (
        UniqueConstraint("cycle_slot_id", "week_start", name="uq_occurrence_slot_week"),
        CheckConstraint("status in ('pending','completed','skipped')", name="ck_occurrence_status"),
        CheckConstraint(f"\"window\" in ({WINDOWS})", name="ck_occurrence_window"),
    )


class SessionTopic(Base):
    __tablename__ = "session_topics"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("study_sessions.id"), primary_key=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), primary_key=True)


class StudySession(Versioned, Base):
    __tablename__ = "study_sessions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    occurrence_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("occurrences.id"), index=True)
    studied_on: Mapped[date] = mapped_column(Date, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    activity: Mapped[str] = mapped_column(String(16))
    essay_kind: Mapped[str | None] = mapped_column(String(16))
    notes: Mapped[str] = mapped_column(Text, default="")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    topic_links: Mapped[list[SessionTopic]] = relationship(
        cascade="all, delete-orphan", order_by=SessionTopic.topic_id, lazy="selectin"
    )
    __table_args__ = (
        CheckConstraint("duration_minutes between 1 and 720", name="ck_session_duration"),
        CheckConstraint("activity in ('theory','questions','review','essay')", name="ck_session_activity"),
        CheckConstraint("activity <> 'essay' or essay_kind is not null", name="ck_session_essay_kind"),
    )

    @property
    def topic_ids(self) -> list[str]:
        return [link.topic_id for link in self.topic_links]


class DailyMission(Base):
    __tablename__ = "daily_missions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    mission_date: Mapped[date] = mapped_column(Date, unique=True)
    kind: Mapped[str] = mapped_column(String(8))
    checkout_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    items: Mapped[list["MissionItem"]] = relationship(
        order_by="MissionItem.position", cascade="all, delete-orphan", lazy="selectin"
    )


class MissionItem(Base):
    __tablename__ = "mission_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("daily_missions.id"))
    position: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))
    ref_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    target: Mapped[int | None] = mapped_column(Integer)
    required: Mapped[bool] = mapped_column(Boolean)
    na_reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("mission_id", "position", name="uq_mission_item_position"),)


class DayOff(Base):
    __tablename__ = "day_offs"
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    reason: Mapped[str] = mapped_column(Text)
```

- [ ] **Step 5: Implementar o seed**

`apps/api/app/seed.py`:

```python
"""Carga idempotente de docs/data. Atualiza catálogo; nunca sobrescreve settings nem dados pessoais."""

import json
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.db import SessionLocal
from app.models import AppSettings, CycleSlot, CycleTemplate, ExamVersion, StudyPlan, Subject, Topic

NAMESPACE = uuid.UUID("6b0d6c8e-2f1a-4c55-9c3e-0c6f5b0a2026")


def stable_id(*parts: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, "/".join(parts))


def load(name: str) -> dict:
    return json.loads((config.DATA_DIR / name).read_text(encoding="utf-8"))


def seed(db: Session) -> None:
    catalog, cycle, game = load("catalogo-edital.json"), load("ciclo-inicial.json"), load("gamificacao.json")
    exam = cycle["exam"]
    source = catalog["source"]

    version = db.get(ExamVersion, catalog["exam_version_id"])
    if version is None:
        version = ExamVersion(
            id=catalog["exam_version_id"],
            exam_id=catalog["exam_id"],
            title=source["title"],
            publication_date=date.fromisoformat(source["publication_date"]),
            source_url=source["url"],
            source_sha256=source["sha256"],
            exam_date=date.fromisoformat(exam["exam_date"]),
            scoring_rules=exam,
        )
        db.add(version)
        db.flush()

    for s_pos, s in enumerate(catalog["subjects"]):
        subject = db.get(Subject, s["id"]) or Subject(id=s["id"], exam_version_id=version.id)
        subject.paper, subject.title, subject.source_ref, subject.position = s["paper"], s["title"], s["source_ref"], s_pos
        db.add(subject)
        for t_pos, t in enumerate(s["topics"]):
            topic = db.get(Topic, t["id"]) or Topic(id=t["id"], subject_id=s["id"])
            topic.title, topic.source_ref, topic.is_summary, topic.position = (
                t["title"], t["source_ref"], t["is_summary"], t_pos,
            )
            db.add(topic)
    db.flush()

    plan_id = stable_id("plan", version.id)
    plan = db.get(StudyPlan, plan_id)
    if plan is None:
        plan = StudyPlan(
            id=plan_id,
            exam_version_id=version.id,
            starts_on=date.fromisoformat(cycle["starts_on"]),
            ends_on=date.fromisoformat(cycle["ends_on"]),
        )
        db.add(plan)
        db.flush()

    effective_from = date.fromisoformat(cycle["template"]["effective_from"])
    template = db.scalar(
        select(CycleTemplate).where(
            CycleTemplate.study_plan_id == plan.id, CycleTemplate.effective_from == effective_from
        )
    )
    if template is None:
        template_id = stable_id("template", str(plan.id), effective_from.isoformat())
        template = CycleTemplate(
            id=template_id,
            study_plan_id=plan.id,
            effective_from=effective_from,
            weekly_minutes=cycle["weekly_minutes"],
            origin=cycle["template"]["origin"],
        )
        template.slots = [
            CycleSlot(
                id=stable_id("slot", str(template_id), s["code"]),
                code=s["code"],
                weekday=s["weekday"],
                window=s["window"],
                minutes=s["minutes"],
                purpose=s["purpose"],
                activity=s["activity"],
                title=s["title"],
                selection_mode=s["selection_mode"],
                candidate_topic_ids=s["candidate_topic_ids"],
                position=i,
            )
            for i, s in enumerate(cycle["slots"])
        ]
        db.add(template)

    if db.get(AppSettings, 1) is None:
        d = game["settings_defaults"]
        db.add(
            AppSettings(
                id=1,
                timezone=d["timezone"],
                weekly_goals=d["weekly_goals"],
                daily_question_goal=d["daily_question_goal"],
                streak_min_minutes=d["streak_min_minutes"],
                max_freezes=d["max_freezes"],
            )
        )
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed(db)
    print("seed ok")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Rodar e ver passar**

Run: `docker compose --profile test run --rm test pytest tests/integration/test_seed.py -q`
Expected: 2 passed.

- [ ] **Step 7: Configurar o Alembic e gerar a migração inicial**

`apps/api/alembic.ini`:

```ini
[alembic]
script_location = migrations
prepend_sys_path = .
file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s

[loggers]
keys = root

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console

[handler_console]
class = StreamHandler
args = (sys.stderr,)
formatter = generic

[formatter_generic]
format = %%(levelname)s %%(name)s %%(message)s
```

`apps/api/migrations/env.py`:

```python
from alembic import context

from app import models  # noqa: F401  (registra as tabelas)
from app.db import Base, engine

target_metadata = Base.metadata


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
```

`apps/api/migrations/script.py.mako`:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

Gerar contra o banco principal `cgu`, ainda vazio. O banco de testes é recriado pelo pytest a cada execução e não serve de base:

```bash
mkdir -p apps/api/migrations/versions
docker compose --profile test run --rm test sh -c 'DATABASE_URL=${DATABASE_URL%_test} alembic revision --autogenerate -m "f1 schema"'
docker compose --profile test run --rm test sh -c 'DATABASE_URL=${DATABASE_URL%_test} alembic upgrade head && DATABASE_URL=${DATABASE_URL%_test} alembic check'
```

Expected: arquivo `migrations/versions/<data>_<rev>_f1_schema.py` criado com 14 `create_table`; a última linha mostra `No new upgrade operations detected.` Abra o arquivo e confirme que contém `'"window" in (...)'` e as constraints `uq_occurrence_slot_week`, `uq_template_plan_effective` e `ck_settings_singleton`.

- [ ] **Step 8: Commit**

```bash
git add .env.example .dockerignore Dockerfile docker-compose.yml ops apps/api
git commit -m "feat(db): compose com Postgres e perfil de testes, modelos F1, migração e seed idempotente"
```

---

### Task 7: Catálogo, plano, semanas e ocorrências (+ snapshot do jogo)

**Files:**
- Create: `apps/api/app/planning/{__init__,service,router}.py`, `apps/api/app/catalog/{__init__,router}.py`, `apps/api/app/game/{__init__,config,snapshot}.py`
- Modify: `apps/api/app/main.py` (registrar `catalog_router` e `planning_router`)
- Test: `apps/api/tests/integration/test_planning.py`

**Interfaces:**
- Consumes: `generate_week`, `select_template`, `suggest_topic`, `week_index`, `week_start_of` (Tarefa 2); funções das Tarefas 3–5; modelos e seed (Tarefa 6).
- Produces:
  - `planning.service.{current_plan(db), templates(db, plan), to_input(template), week_occurrences(db, week_start), ensure_week(db, week_start) -> (list[Occurrence], created), session_stats(db, ids), occurrence_out(occ, stats, plan) -> dict, occurrences_out(db, occs) -> list[dict], list_occurrences(db, start, end), patch_occurrence(db, occ_id, patch: dict) -> Occurrence}`.
  - `game.snapshot.{Snapshot, World, load_world(db), mission_states(world, mission), build_snapshot(db, today), game_delta(before, after) -> dict, tracked(db, today, action) -> (result, delta), summary(db, today) -> dict, ledger(db, today, start, end) -> list[dict]}`.
  - `game.config.{game_config(), xp_table(streak_min), titles(), holiday_suggestions()}`.
  - Rotas: `GET /exam-versions/current`, `GET /subjects`, `PUT /topics/{id}/progress`, `GET /settings`, `GET /plans/current`, `POST /plans/current/weeks`, `GET /occurrences?from=&to=`, `PATCH /occurrences/{id}`.
  - DTO de ocorrência: `id, version, week_start, planned_on, window, status, skip_reason, actual_minutes, completed_on, slot{code,title,purpose,activity,minutes,selection_mode,candidate_topic_ids}, suggested_topic_id`.

- [ ] **Step 1: Escrever o teste que falha**

`apps/api/tests/integration/test_planning.py`:

```python
from datetime import date


def test_generate_partial_first_week(client):
    r = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-05"})
    assert r.status_code == 201
    items = r.json()["items"]
    assert [i["slot"]["code"] for i in items] == ["S13", "S14", "S15"]
    again = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-05"})
    assert again.status_code == 200
    assert [i["id"] for i in again.json()["items"]] == [i["id"] for i in items]


def test_full_week_and_invalid_week(client):
    r = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-12"})
    assert r.status_code == 201
    assert len(r.json()["items"]) == 15
    bad = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-13"})
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "invalid_week"


def test_reschedule_skip_and_reopen(client):
    items = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-12"}).json()["items"]
    occ = items[0]
    moved = client.patch(f"/api/v1/occurrences/{occ['id']}",
                         json={"version": occ["version"], "planned_on": "2026-10-13", "window": "after"})
    assert moved.status_code == 200
    assert (moved.json()["planned_on"], moved.json()["window"]) == ("2026-10-13", "after")
    stale = client.patch(f"/api/v1/occurrences/{occ['id']}", json={"version": occ["version"], "status": "skipped"})
    assert stale.status_code == 409
    skipped = client.patch(f"/api/v1/occurrences/{occ['id']}",
                           json={"version": moved.json()["version"], "status": "skipped", "skip_reason": "feriado"})
    assert skipped.json()["status"] == "skipped"
    reopened = client.patch(f"/api/v1/occurrences/{occ['id']}",
                            json={"version": skipped.json()["version"], "status": "pending"})
    assert (reopened.json()["status"], reopened.json()["skip_reason"]) == ("pending", None)


def test_complete_requires_session(client):
    occ = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-05"}).json()["items"][0]
    r = client.patch(f"/api/v1/occurrences/{occ['id']}", json={"version": occ["version"], "status": "completed"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "session_required"


def test_suggested_topic_alternates(client):
    week1 = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-12"}).json()["items"]
    week2 = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-19"}).json()["items"]
    s01 = lambda items: next(i for i in items if i["slot"]["code"] == "S01")["suggested_topic_id"]
    assert (s01(week1), s01(week2)) == ("B01.01", "B02.01")


def test_catalog_and_progress(client):
    subjects = client.get("/api/v1/subjects").json()["items"]
    assert len(subjects) == 13
    assert sum(len(s["topics"]) for s in subjects) == 68
    r = client.put("/api/v1/topics/E01.02/progress", json={"status": "in_progress"})
    assert r.json()["status"] == "in_progress"
    conflict = client.put("/api/v1/topics/E01.02/progress", json={"status": "first_pass", "version": 99})
    assert conflict.status_code == 409


def test_concurrent_week_generation_returns_existing_week(client, monkeypatch):
    from app.planning import service

    first = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-12"}).json()["items"]
    real = service.week_occurrences
    calls = {"n": 0}

    def racing(db, week_start):
        calls["n"] += 1
        return [] if calls["n"] == 1 else real(db, week_start)

    monkeypatch.setattr(service, "week_occurrences", racing)
    r = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-12"})
    assert r.status_code == 200
    assert sorted(i["id"] for i in r.json()["items"]) == sorted(i["id"] for i in first)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `docker compose --profile test run --rm test pytest tests/integration/test_planning.py -q`
Expected: FAIL; as rotas respondem 404 (`assert 404 == 201`).

- [ ] **Step 3: Implementar o serviço de planejamento**

`apps/api/app/planning/service.py`:

```python
import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.cycle import (
    CycleError,
    SlotInput,
    TemplateInput,
    generate_week,
    select_template,
    suggest_topic,
    week_index,
)
from app.errors import ApiError
from app.models import CycleTemplate, Occurrence, StudyPlan, StudySession


def current_plan(db: Session) -> StudyPlan:
    plan = db.scalar(select(StudyPlan).order_by(StudyPlan.starts_on.desc()).limit(1))
    if plan is None:
        raise ApiError(404, "plan_missing", "Plano não encontrado. Rode o seed.")
    return plan


def templates(db: Session, plan: StudyPlan) -> list[CycleTemplate]:
    return list(db.scalars(select(CycleTemplate).where(CycleTemplate.study_plan_id == plan.id)))


def to_input(template: CycleTemplate) -> TemplateInput:
    slots = tuple(SlotInput(s.code, s.weekday, s.window, s.minutes, s.purpose) for s in template.slots)
    return TemplateInput(template.effective_from, slots)


def week_occurrences(db: Session, week_start: date) -> list[Occurrence]:
    rows = db.scalars(select(Occurrence).where(Occurrence.week_start == week_start))
    return sorted(rows, key=lambda o: (o.planned_on, o.slot.position))


def ensure_week(db: Session, week_start: date) -> tuple[list[Occurrence], bool]:
    """Gera a semana se ainda não existir. Retorna (ocorrências, criou_agora)."""
    existing = week_occurrences(db, week_start)
    if existing:
        return existing, False
    plan = current_plan(db)
    rows = templates(db, plan)
    try:
        chosen_input = select_template([to_input(t) for t in rows], week_start)
        generated = generate_week(chosen_input, week_start, plan.starts_on, plan.ends_on)
    except CycleError as exc:
        raise ApiError(422, "invalid_week", str(exc), {"week_start": str(exc)}) from exc
    template = next(t for t in rows if t.effective_from == chosen_input.effective_from)
    slot_by_code = {s.code: s for s in template.slots}
    occurrences = [
        Occurrence(
            id=uuid.uuid4(),
            cycle_slot_id=slot_by_code[o.cycle_slot_code].id,
            week_start=o.week_start,
            planned_on=o.planned_on,
            window=o.window,
            status="pending",
        )
        for o in generated
    ]
    db.add_all(occurrences)
    db.flush()
    return week_occurrences(db, week_start), True


def session_stats(db: Session, occurrence_ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[int, date | None]]:
    """Minutos ativos e data de conclusão derivada (maior studied_on) por ocorrência."""
    if not occurrence_ids:
        return {}
    rows = db.execute(
        select(StudySession.occurrence_id, func.sum(StudySession.duration_minutes), func.max(StudySession.studied_on))
        .where(StudySession.occurrence_id.in_(occurrence_ids), StudySession.deleted_at.is_(None))
        .group_by(StudySession.occurrence_id)
    )
    stats: dict[uuid.UUID, tuple[int, date | None]] = defaultdict(lambda: (0, None))
    for occ_id, minutes, last_day in rows:
        stats[occ_id] = (int(minutes), last_day)
    return stats


def occurrence_out(occ: Occurrence, stats: dict, plan: StudyPlan) -> dict:
    minutes, last_day = stats.get(occ.id, (0, None))
    slot = occ.slot
    return {
        "id": str(occ.id),
        "version": occ.version,
        "week_start": occ.week_start,
        "planned_on": occ.planned_on,
        "window": occ.window,
        "status": occ.status,
        "skip_reason": occ.skip_reason,
        "actual_minutes": minutes,
        "completed_on": last_day if occ.status == "completed" else None,
        "slot": {
            "code": slot.code,
            "title": slot.title,
            "purpose": slot.purpose,
            "activity": slot.activity,
            "minutes": slot.minutes,
            "selection_mode": slot.selection_mode,
            "candidate_topic_ids": slot.candidate_topic_ids,
        },
        "suggested_topic_id": suggest_topic(
            slot.selection_mode, slot.candidate_topic_ids, week_index(occ.week_start, plan.starts_on)
        ),
    }


def occurrences_out(db: Session, occurrences: list[Occurrence]) -> list[dict]:
    plan = current_plan(db)
    stats = session_stats(db, [o.id for o in occurrences])
    return [occurrence_out(o, stats, plan) for o in occurrences]


def list_occurrences(db: Session, start: date, end: date) -> list[Occurrence]:
    rows = db.scalars(select(Occurrence).where(Occurrence.planned_on.between(start, end)))
    return sorted(rows, key=lambda o: (o.planned_on, o.slot.position))


def patch_occurrence(db: Session, occ_id: uuid.UUID, patch: dict) -> Occurrence:
    occ = db.get(Occurrence, occ_id)
    if occ is None:
        raise ApiError(404, "not_found", "Bloco não encontrado.")
    if patch["version"] != occ.version:
        raise ApiError(409, "version_conflict", "Este registro foi alterado. Recarregue antes de editar.")
    moving = patch.get("planned_on") is not None or patch.get("window") is not None
    if moving:
        if occ.status != "pending":
            raise ApiError(422, "not_pending", "Só blocos pendentes podem ser remanejados.")
        plan = current_plan(db)
        target = patch.get("planned_on") or occ.planned_on
        if not plan.starts_on <= target <= plan.ends_on:
            raise ApiError(422, "outside_plan", "Data fora do plano.", {"planned_on": "Fora do plano."})
        occ.planned_on = target
        occ.window = patch.get("window") or occ.window
    status = patch.get("status")
    if status == "completed":
        minutes, _ = session_stats(db, [occ.id]).get(occ.id, (0, None))
        if minutes == 0:
            raise ApiError(422, "session_required", "Registre uma sessão antes de concluir o bloco.")
    if status == "skipped":
        occ.skip_reason = patch.get("skip_reason")
    if status == "pending":
        occ.skip_reason = None
    if status:
        occ.status = status
    occ.version += 1
    db.flush()
    return occ
```

- [ ] **Step 4: Implementar a configuração e o snapshot do jogo**

`apps/api/app/game/config.py`:

```python
import json
from functools import lru_cache

from app import config
from app.domain.xp import TitleBand, XpTable


@lru_cache
def game_config() -> dict:
    return json.loads((config.DATA_DIR / "gamificacao.json").read_text(encoding="utf-8"))


def xp_table(streak_min_minutes: int) -> XpTable:
    xp = game_config()["xp"]
    return XpTable(
        per_session_minute=xp["per_session_minute"],
        session_minutes_daily_cap=xp["session_minutes_daily_cap"],
        block_completed=xp["block_completed"],
        mission_complete=xp["mission_complete"],
        mission_optional_item=xp["mission_optional_item"],
        week_complete=xp["week_complete"],
        weekend_active_day=xp["weekend_active_day"],
        weekend_min_minutes=streak_min_minutes,
    )


def titles() -> tuple[TitleBand, ...]:
    return tuple(TitleBand(t["from"], t["to"], t["title"]) for t in game_config()["levels"]["titles"])


def holiday_suggestions() -> list[dict]:
    return game_config().get("holiday_suggestions", [])
```

`apps/api/app/game/snapshot.py`:

```python
"""Snapshot do jogo: monta fatos a partir do banco e chama as funções puras (R14)."""

import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import mission as mission_domain
from app.domain.streak import StreakState, streak_state
from app.domain.weeks import is_week_complete, minutes_goal_for_week
from app.domain.xp import BlockFact, GameFacts, LevelInfo, MissionFact, SessionFact, XpEntry, level_for_xp, xp_ledger
from app.game import config as game_config
from app.models import AppSettings, DailyMission, DayOff, MissionItem, Occurrence, StudySession
from app.planning.service import current_plan

T = TypeVar("T")


@dataclass
class Snapshot:
    ledger: list[XpEntry]
    total: int
    level: LevelInfo
    streak: StreakState
    mission_complete: dict[date, bool]


@dataclass
class World:
    """Registros ativos carregados uma vez por cálculo."""
    occurrences: dict[uuid.UUID, Occurrence]
    completed_on: dict[uuid.UUID, date]
    minutes_by_date: dict[date, int]
    sessions: list[SessionFact]


def load_world(db: Session) -> World:
    occurrences = {o.id: o for o in db.scalars(select(Occurrence))}
    rows = db.execute(
        select(StudySession.id, StudySession.occurrence_id, StudySession.studied_on, StudySession.duration_minutes)
        .where(StudySession.deleted_at.is_(None))
    ).all()
    completed_on: dict[uuid.UUID, date] = {}
    minutes_by_date: dict[date, int] = defaultdict(int)
    for _, occ_id, studied_on, minutes in rows:
        minutes_by_date[studied_on] += minutes
        if occ_id is not None and occurrences[occ_id].status == "completed":
            completed_on[occ_id] = max(completed_on.get(occ_id, studied_on), studied_on)
    sessions = [SessionFact(str(sid), studied_on, minutes) for sid, _, studied_on, minutes in rows]
    return World(occurrences, completed_on, dict(minutes_by_date), sessions)


def day_facts(world: World, mission: DailyMission) -> mission_domain.DayFacts:
    refs = [i.ref_id for i in mission.items if i.kind == "block" and i.ref_id is not None]
    return mission_domain.DayFacts(
        mission_date=mission.mission_date,
        occurrence_status={str(r): world.occurrences[r].status for r in refs},
        occurrence_planned_on={str(r): world.occurrences[r].planned_on for r in refs},
        occurrence_completed_on={str(r): world.completed_on[r] for r in refs if r in world.completed_on},
        question_items=0,
        checkout_saved=bool(mission.checkout_note and mission.checkout_note.strip()),
    )


def item_input(item: MissionItem) -> mission_domain.MissionItemInput:
    return mission_domain.MissionItemInput(
        item.position, item.kind, item.required, str(item.ref_id) if item.ref_id else None, item.target, item.na_reason
    )


def mission_states(world: World, mission: DailyMission) -> list[tuple[MissionItem, mission_domain.ItemState]]:
    facts = day_facts(world, mission)
    return [(item, mission_domain.item_state(item_input(item), facts)) for item in mission.items]


def complete_weeks(db: Session, world: World) -> frozenset[date]:
    settings = db.get(AppSettings, 1)
    plan = current_plan(db)
    by_week: dict[date, list[Occurrence]] = defaultdict(list)
    for occ in world.occurrences.values():
        by_week[occ.week_start].append(occ)
    done = set()
    for ws, occs in by_week.items():
        minutes = sum(world.minutes_by_date.get(ws + timedelta(days=i), 0) for i in range(7))
        goal = minutes_goal_for_week(ws, plan.starts_on, sum(o.slot.minutes for o in occs),
                                     settings.weekly_goals["minutes"])
        if is_week_complete([o.status for o in occs], minutes, goal):
            done.add(ws)
    return frozenset(done)


def build_snapshot(db: Session, today: date) -> Snapshot:
    settings = db.get(AppSettings, 1)
    plan = current_plan(db)
    world = load_world(db)
    missions = list(db.scalars(select(DailyMission)))
    mission_facts, mission_complete = [], {}
    for m in missions:
        pairs = [(item.required, state) for item, state in mission_states(world, m)]
        complete = mission_domain.is_complete(pairs)
        mission_complete[m.mission_date] = complete
        mission_facts.append(MissionFact(str(m.id), m.mission_date, complete, mission_domain.optional_done(pairs)))
    weeks = complete_weeks(db, world)
    facts = GameFacts(
        sessions=tuple(world.sessions),
        blocks=tuple(BlockFact(str(oid), d) for oid, d in world.completed_on.items()),
        missions=tuple(mission_facts),
        complete_week_starts=weeks,
    )
    ledger = xp_ledger(facts, game_config.xp_table(settings.streak_min_minutes))
    total = sum(e.xp for e in ledger)
    day_offs = set(db.scalars(select(DayOff.day)))
    streak = streak_state(world.minutes_by_date, day_offs, set(weeks), plan.starts_on, today,
                          settings.streak_min_minutes, settings.max_freezes)
    return Snapshot(ledger, total, level_for_xp(total, game_config.titles()), streak, mission_complete)


def game_delta(before: Snapshot, after: Snapshot) -> dict:
    old = {(e.source, e.ref_id, e.date): e.xp for e in before.ledger}
    new = {(e.source, e.ref_id, e.date): e.xp for e in after.ledger}
    entries = [
        {"source": k[0], "ref_id": k[1], "date": k[2], "xp": new.get(k, 0) - old.get(k, 0)}
        for k in sorted(set(old) | set(new), key=lambda k: (k[2], k[0], k[1]))
        if new.get(k, 0) != old.get(k, 0)
    ]
    return {
        "xp_gained": after.total - before.total,
        "entries": entries,
        "level_up": after.level.level if after.level.level > before.level.level else None,
        "mission_complete": sorted(
            d for d, c in after.mission_complete.items() if c and not before.mission_complete.get(d)
        ),
        "streak": after.streak.current,
    }


def tracked(db: Session, today: date, action: Callable[[], T]) -> tuple[T, dict]:
    """Executa uma mutação em transação e devolve o efeito no jogo."""
    before = build_snapshot(db, today)
    result = action()
    db.flush()
    after = build_snapshot(db, today)
    db.commit()
    return result, game_delta(before, after)


def summary(db: Session, today: date) -> dict:
    snap = build_snapshot(db, today)
    plan = current_plan(db)
    settings = db.get(AppSettings, 1)
    exam_date = plan.exam_version.exam_date
    marked = set(db.scalars(select(DayOff.day)))
    upcoming = [h for h in game_config.holiday_suggestions()
                if date.fromisoformat(h["date"]) in (today, today + timedelta(days=1))
                and date.fromisoformat(h["date"]) not in marked]
    return {
        "today": today,
        "exam_date": exam_date,
        "days_to_exam": (exam_date - today).days,
        "xp_total": snap.total,
        "level": snap.level.level,
        "title": snap.level.title,
        "xp_into_level": snap.level.xp_into_level,
        "xp_for_next": snap.level.xp_for_next,
        "streak": {
            "current": snap.streak.current,
            "best": snap.streak.best,
            "freezes_available": snap.streak.freezes_available,
            "frozen_days": list(snap.streak.frozen_days),
            "at_stake_today": snap.streak.at_stake_today,
            "minutes_today": snap.streak.minutes_today,
            "min_minutes": settings.streak_min_minutes,
        },
        "holiday_suggestion": upcoming[0] if upcoming else None,
    }


def ledger(db: Session, today: date, start: date, end: date) -> list[dict]:
    snap = build_snapshot(db, today)
    return [{"date": e.date, "source": e.source, "ref_id": e.ref_id, "xp": e.xp}
            for e in snap.ledger if start <= e.date <= end]
```

- [ ] **Step 5: Implementar os roteadores**

`apps/api/app/planning/router.py`:

```python
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import get_db
from app.game.snapshot import tracked
from app.planning import service

router = APIRouter(tags=["planning"])


class WeekIn(BaseModel):
    week_start: date


class OccurrencePatch(BaseModel):
    version: int
    planned_on: date | None = None
    window: Literal["before", "middle", "after"] | None = None
    status: Literal["pending", "completed", "skipped"] | None = None
    skip_reason: str | None = None


@router.get("/plans/current")
def get_plan(db: Session = Depends(get_db)):
    plan = service.current_plan(db)
    return {
        "id": str(plan.id),
        "starts_on": plan.starts_on,
        "ends_on": plan.ends_on,
        "exam_date": plan.exam_version.exam_date,
        "templates": [
            {
                "id": str(t.id),
                "effective_from": t.effective_from,
                "weekly_minutes": t.weekly_minutes,
                "origin": t.origin,
                "slots": [
                    {"code": s.code, "weekday": s.weekday, "window": s.window, "minutes": s.minutes,
                     "purpose": s.purpose, "activity": s.activity, "title": s.title}
                    for s in t.slots
                ],
            }
            for t in sorted(service.templates(db, plan), key=lambda t: t.effective_from)
        ],
    }


@router.post("/plans/current/weeks")
def create_week(body: WeekIn, response: Response, db: Session = Depends(get_db),
                today: date = Depends(get_today)):
    def action():
        return service.ensure_week(db, body.week_start)

    try:
        (occurrences, created), delta = tracked(db, today, action)
    except IntegrityError:
        # Geração concorrente da mesma semana: a segunda tentativa devolve a semana já gravada.
        db.rollback()
        (occurrences, created), delta = tracked(db, today, action)
    response.status_code = 201 if created else 200
    return {"week_start": body.week_start, "items": service.occurrences_out(db, occurrences), "game_delta": delta}


@router.get("/occurrences")
def get_occurrences(from_: date = Query(alias="from"), to: date = Query(), db: Session = Depends(get_db)):
    items = service.occurrences_out(db, service.list_occurrences(db, from_, to))
    return {"items": items, "total": len(items)}


@router.patch("/occurrences/{occ_id}")
def update_occurrence(occ_id: uuid.UUID, body: OccurrencePatch, db: Session = Depends(get_db),
                      today: date = Depends(get_today)):
    occ, delta = tracked(db, today, lambda: service.patch_occurrence(db, occ_id, body.model_dump()))
    return {**service.occurrences_out(db, [occ])[0], "game_delta": delta}
```

`apps/api/app/catalog/router.py`:

```python
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.clock import get_today
from app.db import get_db
from app.errors import ApiError
from app.models import AppSettings, ExamVersion, Subject, Topic, TopicProgress

router = APIRouter(tags=["catalog"])


class ProgressIn(BaseModel):
    status: Literal["not_started", "in_progress", "first_pass", "reviewed"]
    version: int | None = None


def progress_out(p: TopicProgress | None) -> dict | None:
    if p is None:
        return None
    return {"status": p.status, "declared_on": p.declared_on, "version": p.version}


@router.get("/exam-versions/current")
def current_exam_version(db: Session = Depends(get_db)):
    ev = db.scalar(select(ExamVersion).order_by(ExamVersion.publication_date.desc()).limit(1))
    if ev is None:
        raise ApiError(404, "not_found", "Versão do edital não carregada.")
    return {"id": ev.id, "title": ev.title, "publication_date": ev.publication_date, "source_url": ev.source_url,
            "source_sha256": ev.source_sha256, "exam_date": ev.exam_date, "scoring_rules": ev.scoring_rules}


@router.get("/subjects")
def list_subjects(db: Session = Depends(get_db)):
    progress = {p.topic_id: p for p in db.scalars(select(TopicProgress))}
    subjects = db.scalars(select(Subject).options(selectinload(Subject.topics)).order_by(Subject.position))
    items = [
        {"id": s.id, "paper": s.paper, "title": s.title, "source_ref": s.source_ref,
         "topics": [{"id": t.id, "title": t.title, "source_ref": t.source_ref,
                     "progress": progress_out(progress.get(t.id))} for t in s.topics]}
        for s in subjects
    ]
    return {"items": items, "total": len(items)}


@router.put("/topics/{topic_id}/progress")
def put_progress(topic_id: str, body: ProgressIn, db: Session = Depends(get_db), today: date = Depends(get_today)):
    if db.get(Topic, topic_id) is None:
        raise ApiError(404, "not_found", "Tópico não encontrado.")
    row = db.get(TopicProgress, topic_id)
    if row is None:
        row = TopicProgress(topic_id=topic_id, status=body.status, declared_on=today)
        db.add(row)
    else:
        if body.version != row.version:
            raise ApiError(409, "version_conflict", "Este registro foi alterado. Recarregue antes de editar.")
        row.status, row.declared_on = body.status, today
        row.version += 1
    db.commit()
    return {"topic_id": topic_id, **progress_out(row)}


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    s = db.get(AppSettings, 1)
    return {"timezone": s.timezone, "weekly_goals": s.weekly_goals, "daily_question_goal": s.daily_question_goal,
            "streak_min_minutes": s.streak_min_minutes, "max_freezes": s.max_freezes, "version": s.version}
```

`apps/api/app/main.py`: acrescentar os imports e registrar os roteadores:

```python
from app.catalog.router import router as catalog_router
from app.planning.router import router as planning_router
```

```python
    for router in (catalog_router, planning_router):
        api.include_router(router)
```

```bash
touch apps/api/app/planning/__init__.py apps/api/app/catalog/__init__.py apps/api/app/game/__init__.py
```

- [ ] **Step 6: Rodar e ver passar**

Run: `docker compose --profile test run --rm test pytest tests/integration/test_planning.py -q`
Expected: 7 passed.

- [ ] **Step 7: Commit**

```bash
git add apps/api
git commit -m "feat(api): catálogo, plano, geração de semanas e ocorrências com game_delta"
```

---

### Task 8: Sessões de estudo

**Files:**
- Create: `apps/api/app/study/{__init__,service,router}.py`
- Modify: `apps/api/app/main.py` (registrar `study_router`)
- Test: `apps/api/tests/integration/test_sessions.py`

**Interfaces:**
- Consumes: `game.snapshot.tracked`; modelos `Occurrence`, `StudySession`, `SessionTopic`, `Topic`.
- Produces: `study.service.{SessionIn, SessionPatch, create_session(db, data, today) -> (StudySession, created), update_session(db, id, patch, today), delete_session(db, id), list_sessions(db, start, end, limit, offset), session_out(s) -> dict, active_minutes(db, occurrence_id)}`; rotas `POST/PATCH/DELETE/GET /sessions`. Corpo de criação: `id, occurrence_id?, studied_on, duration_minutes, activity, essay_kind?, topic_ids, notes, complete_occurrence`.

- [ ] **Step 1: Escrever o teste que falha**

`apps/api/tests/integration/test_sessions.py`:

```python
import uuid


def friday_blocks(client):
    return client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-05"}).json()["items"]


def friday_occurrence(client, occ_id):
    items = client.get("/api/v1/occurrences", params={"from": "2026-10-09", "to": "2026-10-09"}).json()["items"]
    return next(o for o in items if o["id"] == occ_id)


def payload(**over):
    body = {"id": str(uuid.uuid4()), "studied_on": "2026-10-09", "duration_minutes": 50,
            "activity": "theory", "topic_ids": ["C02.01", "C04.01"], "notes": "LAI"}
    body.update(over)
    return body


def test_create_session_counts_minutes_once_and_completes_block(client):
    occ = friday_blocks(client)[0]
    r = client.post("/api/v1/sessions", json=payload(occurrence_id=occ["id"], complete_occurrence=True))
    assert r.status_code == 201
    assert r.json()["topic_ids"] == ["C02.01", "C04.01"]
    assert r.json()["game_delta"]["xp_gained"] == 50 + 20
    first = friday_occurrence(client, occ["id"])
    assert (first["status"], first["actual_minutes"], first["completed_on"]) == ("completed", 50, "2026-10-09")


def test_resend_same_id_is_idempotent_and_conflict_on_different_payload(client):
    body = payload()
    assert client.post("/api/v1/sessions", json=body).status_code == 201
    again = client.post("/api/v1/sessions", json=body)
    assert again.status_code == 200
    assert again.json()["game_delta"]["xp_gained"] == 0
    listed = client.get("/api/v1/sessions", params={"from": "2026-10-01", "to": "2026-10-31"}).json()
    assert listed["total"] == 1
    conflict = client.post("/api/v1/sessions", json={**body, "duration_minutes": 51})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "duplicate_id_conflict"


def test_validation(client, clock):
    assert client.post("/api/v1/sessions", json=payload(duration_minutes=0)).status_code == 422
    assert client.post("/api/v1/sessions", json=payload(duration_minutes=721)).status_code == 422
    assert client.post("/api/v1/sessions", json=payload(topic_ids=[])).status_code == 422
    assert client.post("/api/v1/sessions", json=payload(topic_ids=["X99.99"])).status_code == 422
    future = client.post("/api/v1/sessions", json=payload(studied_on="2026-10-10"))
    assert future.status_code == 422
    assert future.json()["error"]["fields"] == {"studied_on": "Data futura."}


def test_essay_session_without_topics(client):
    essay_block = friday_blocks(client)[1]
    r = client.post("/api/v1/sessions", json=payload(
        occurrence_id=essay_block["id"], activity="essay", essay_kind="complementary", topic_ids=[],
        complete_occurrence=True))
    assert r.status_code == 201
    no_kind = client.post("/api/v1/sessions", json=payload(activity="essay", topic_ids=[]))
    assert no_kind.status_code == 422


def test_edit_with_version_and_delete_reopens_block(client):
    occ = friday_blocks(client)[0]
    created = client.post("/api/v1/sessions", json=payload(occurrence_id=occ["id"], complete_occurrence=True)).json()
    edited = client.patch(f"/api/v1/sessions/{created['id']}", json={"version": created["version"], "duration_minutes": 40})
    assert edited.status_code == 200
    assert edited.json()["game_delta"]["xp_gained"] == -10
    stale = client.patch(f"/api/v1/sessions/{created['id']}", json={"version": created["version"], "notes": "x"})
    assert stale.status_code == 409
    assert client.delete(f"/api/v1/sessions/{created['id']}").status_code == 204
    assert friday_occurrence(client, occ["id"])["status"] == "pending"


def test_studied_on_is_kept_as_sent(client, clock):
    from datetime import date
    clock.today = date(2026, 10, 12)
    created = client.post("/api/v1/sessions", json=payload(studied_on="2026-10-09")).json()
    assert created["studied_on"] == "2026-10-09"


def test_skipped_block_rejects_session_and_completed_block_cannot_move(client):
    skipped, done = friday_blocks(client)[0], friday_blocks(client)[2]
    client.patch(f"/api/v1/occurrences/{skipped['id']}", json={"version": skipped["version"], "status": "skipped"})
    r = client.post("/api/v1/sessions", json=payload(occurrence_id=skipped["id"]))
    assert (r.status_code, r.json()["error"]["code"]) == (422, "occurrence_skipped")
    client.post("/api/v1/sessions", json=payload(occurrence_id=done["id"], complete_occurrence=True))
    current = friday_occurrence(client, done["id"])
    move = client.patch(f"/api/v1/occurrences/{done['id']}", json={"version": current["version"], "planned_on": "2026-10-12"})
    assert (move.status_code, move.json()["error"]["code"]) == (422, "not_pending")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `docker compose --profile test run --rm test pytest tests/integration/test_sessions.py -q`
Expected: FAIL; `POST /sessions` responde 404.

- [ ] **Step 3: Implementar o serviço**

`apps/api/app/study/service.py`:

```python
import uuid
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import Occurrence, SessionTopic, StudySession, Topic

Activity = Literal["theory", "questions", "review", "essay"]
EssayKind = Literal["complementary", "technical_case"]


class SessionIn(BaseModel):
    id: uuid.UUID
    occurrence_id: uuid.UUID | None = None
    studied_on: date
    duration_minutes: int = Field(ge=1, le=720)
    activity: Activity
    essay_kind: EssayKind | None = None
    topic_ids: list[str] = []
    notes: str = Field(default="", max_length=2000)
    complete_occurrence: bool = False

    @model_validator(mode="after")
    def check_activity(self):
        if self.activity == "essay" and self.essay_kind is None:
            raise ValueError("Discursiva exige essay_kind.")
        if self.activity != "essay" and not self.topic_ids:
            raise ValueError("Informe ao menos um tópico.")
        if self.activity != "essay" and self.essay_kind is not None:
            raise ValueError("essay_kind só vale para discursiva.")
        return self


class SessionPatch(BaseModel):
    version: int
    studied_on: date | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=720)
    topic_ids: list[str] | None = None
    notes: str | None = Field(default=None, max_length=2000)


def _fingerprint(occurrence_id, studied_on, minutes, activity, essay_kind, topic_ids, notes) -> tuple:
    return (
        str(occurrence_id) if occurrence_id else None, studied_on, minutes, activity, essay_kind,
        tuple(sorted(set(topic_ids))), notes,
    )


def _check_not_future(studied_on: date, today: date) -> None:
    if studied_on > today:
        raise ApiError(422, "future_date", "A data do estudo não pode ser futura.", {"studied_on": "Data futura."})


def _check_topics(db: Session, topic_ids: list[str]) -> None:
    wanted = set(topic_ids)
    found = set(db.scalars(select(Topic.id).where(Topic.id.in_(wanted))))
    missing = sorted(wanted - found)
    if missing:
        raise ApiError(422, "unknown_topic", "Tópico inexistente.", {"topic_ids": ", ".join(missing)})


def active_minutes(db: Session, occurrence_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.coalesce(func.sum(StudySession.duration_minutes), 0)).where(
            StudySession.occurrence_id == occurrence_id, StudySession.deleted_at.is_(None)
        )
    )


def session_out(s: StudySession) -> dict:
    return {
        "id": str(s.id),
        "version": s.version,
        "occurrence_id": str(s.occurrence_id) if s.occurrence_id else None,
        "studied_on": s.studied_on,
        "duration_minutes": s.duration_minutes,
        "activity": s.activity,
        "essay_kind": s.essay_kind,
        "topic_ids": s.topic_ids,
        "notes": s.notes,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


def create_session(db: Session, data: SessionIn, today: date) -> tuple[StudySession, bool]:
    existing = db.get(StudySession, data.id)
    if existing is not None:
        same = _fingerprint(
            existing.occurrence_id, existing.studied_on, existing.duration_minutes, existing.activity,
            existing.essay_kind, existing.topic_ids, existing.notes,
        ) == _fingerprint(
            data.occurrence_id, data.studied_on, data.duration_minutes, data.activity, data.essay_kind,
            data.topic_ids, data.notes,
        )
        if same:
            return existing, False
        raise ApiError(409, "duplicate_id_conflict", "Já existe um registro com este id e conteúdo diferente.")
    _check_not_future(data.studied_on, today)
    _check_topics(db, data.topic_ids)
    occurrence = None
    if data.occurrence_id is not None:
        occurrence = db.get(Occurrence, data.occurrence_id)
        if occurrence is None:
            raise ApiError(422, "unknown_occurrence", "Bloco inexistente.", {"occurrence_id": "Inexistente."})
        if occurrence.status == "skipped":
            raise ApiError(422, "occurrence_skipped", "Bloco dispensado: reabra antes de registrar.")
    session = StudySession(
        id=data.id,
        occurrence_id=data.occurrence_id,
        studied_on=data.studied_on,
        duration_minutes=data.duration_minutes,
        activity=data.activity,
        essay_kind=data.essay_kind,
        notes=data.notes,
        topic_links=[SessionTopic(topic_id=t) for t in sorted(set(data.topic_ids))],
    )
    db.add(session)
    db.flush()
    if data.complete_occurrence and occurrence is not None and occurrence.status == "pending":
        occurrence.status = "completed"
        occurrence.version += 1
        db.flush()
    return session, True


def update_session(db: Session, session_id: uuid.UUID, patch: SessionPatch, today: date) -> StudySession:
    session = db.get(StudySession, session_id)
    if session is None or session.deleted_at is not None:
        raise ApiError(404, "not_found", "Sessão não encontrada.")
    if patch.version != session.version:
        raise ApiError(409, "version_conflict", "Este registro foi alterado. Recarregue antes de editar.")
    if patch.studied_on is not None:
        _check_not_future(patch.studied_on, today)
        session.studied_on = patch.studied_on
    if patch.duration_minutes is not None:
        session.duration_minutes = patch.duration_minutes
    if patch.notes is not None:
        session.notes = patch.notes
    if patch.topic_ids is not None:
        if session.activity != "essay" and not patch.topic_ids:
            raise ApiError(422, "topic_required", "Informe ao menos um tópico.", {"topic_ids": "Obrigatório."})
        _check_topics(db, patch.topic_ids)
        session.topic_links = [SessionTopic(topic_id=t) for t in sorted(set(patch.topic_ids))]
    session.version += 1
    db.flush()
    return session


def delete_session(db: Session, session_id: uuid.UUID) -> None:
    session = db.get(StudySession, session_id)
    if session is None:
        raise ApiError(404, "not_found", "Sessão não encontrada.")
    if session.deleted_at is not None:
        return
    session.deleted_at = datetime.now(timezone.utc)
    session.version += 1
    db.flush()
    if session.occurrence_id is not None:
        occurrence = db.get(Occurrence, session.occurrence_id)
        if occurrence.status == "completed" and active_minutes(db, occurrence.id) == 0:
            occurrence.status = "pending"
            occurrence.version += 1
            db.flush()


def list_sessions(db: Session, start: date, end: date, limit: int, offset: int) -> tuple[list[StudySession], int]:
    where = (StudySession.deleted_at.is_(None), StudySession.studied_on.between(start, end))
    total = db.scalar(select(func.count()).select_from(StudySession).where(*where))
    rows = db.scalars(
        select(StudySession).where(*where)
        .order_by(StudySession.studied_on.desc(), StudySession.created_at.desc())
        .limit(limit).offset(offset)
    )
    return list(rows), total
```

- [ ] **Step 4: Implementar o roteador e registrá-lo**

`apps/api/app/study/router.py`:

```python
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import get_db
from app.game.snapshot import tracked
from app.study import service

router = APIRouter(tags=["sessions"])


@router.post("/sessions")
def create_session(body: service.SessionIn, response: Response, db: Session = Depends(get_db),
                   today: date = Depends(get_today)):
    (session, created), delta = tracked(db, today, lambda: service.create_session(db, body, today))
    response.status_code = 201 if created else 200
    return {**service.session_out(session), "game_delta": delta}


@router.patch("/sessions/{session_id}")
def update_session(session_id: uuid.UUID, body: service.SessionPatch, db: Session = Depends(get_db),
                   today: date = Depends(get_today)):
    session, delta = tracked(db, today, lambda: service.update_session(db, session_id, body, today))
    return {**service.session_out(session), "game_delta": delta}


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: uuid.UUID, db: Session = Depends(get_db), today: date = Depends(get_today)):
    tracked(db, today, lambda: service.delete_session(db, session_id))
    return Response(status_code=204)


@router.get("/sessions")
def list_sessions(
    from_: date = Query(alias="from"), to: date = Query(),
    limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    rows, total = service.list_sessions(db, from_, to, limit, offset)
    return {"items": [service.session_out(s) for s in rows], "total": total, "limit": limit, "offset": offset}
```

`apps/api/app/main.py`:

```python
from app.study.router import router as study_router
```

```python
    for router in (catalog_router, planning_router, study_router):
```

```bash
touch apps/api/app/study/__init__.py
```

- [ ] **Step 5: Rodar e ver passar**

Run: `docker compose --profile test run --rm test pytest tests/integration/test_sessions.py -q`
Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add apps/api
git commit -m "feat(api): sessões com UUID do cliente, versão, conclusão de bloco e exclusão lógica"
```

---

### Task 9: Resumo do jogo, extrato de XP e folgas

**Files:**
- Create: `apps/api/app/game/router.py`
- Modify: `apps/api/app/main.py` (registrar `game_router`)
- Test: `apps/api/tests/integration/test_game.py`

**Interfaces:**
- Consumes: `game.snapshot.{summary, ledger, tracked}`, `game.config.game_config`.
- Produces: `GET /game/summary` → `{today, exam_date, days_to_exam, xp_total, level, title, xp_into_level, xp_for_next, streak{current,best,freezes_available,frozen_days,at_stake_today,minutes_today,min_minutes}, holiday_suggestion}`; `GET /game/xp?from=&to=`; `GET /game/config`; `GET /day-offs`; `PUT /day-offs/{day}` (`{reason}`; fim de semana → 422); `DELETE /day-offs/{day}`.

- [ ] **Step 1: Escrever o teste que falha**

`apps/api/tests/integration/test_game.py`:

```python
import uuid
from datetime import date, timedelta


def study(client, day: date, minutes: int):
    body = {"id": str(uuid.uuid4()), "studied_on": day.isoformat(), "duration_minutes": minutes,
            "activity": "theory", "topic_ids": ["E01.02"]}
    assert client.post("/api/v1/sessions", json=body).status_code == 201


def test_summary_empty_state(client):
    s = client.get("/api/v1/game/summary").json()
    assert (s["xp_total"], s["level"], s["title"], s["days_to_exam"]) == (0, 1, "Estagiário", 65)
    assert s["streak"]["current"] == 0
    assert s["streak"]["at_stake_today"] is True


def test_streak_with_day_off_and_break(client, clock):
    study(client, date(2026, 10, 9), 45)
    clock.today = date(2026, 10, 14)
    study(client, date(2026, 10, 12), 30)
    assert client.get("/api/v1/game/summary").json()["streak"]["current"] == 0
    r = client.put("/api/v1/day-offs/2026-10-13", json={"reason": "compromisso"})
    assert r.status_code == 200
    s = client.get("/api/v1/game/summary").json()["streak"]
    assert (s["current"], s["best"]) == (2, 2)
    assert client.delete("/api/v1/day-offs/2026-10-13").status_code == 204
    assert client.get("/api/v1/game/summary").json()["streak"]["current"] == 0


def test_weekend_day_off_rejected(client):
    assert client.put("/api/v1/day-offs/2026-10-10", json={"reason": "x"}).status_code == 422


def test_holiday_suggestion_on_eve(client, clock):
    clock.today = date(2026, 10, 11)
    assert client.get("/api/v1/game/summary").json()["holiday_suggestion"]["date"] == "2026-10-12"
    client.put("/api/v1/day-offs/2026-10-12", json={"reason": "Nossa Senhora Aparecida"})
    assert client.get("/api/v1/game/summary").json()["holiday_suggestion"] is None


def test_full_week_completion_grants_xp_and_freeze(client, clock):
    clock.today = date(2026, 10, 20)
    client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-12"})
    for i in range(5):
        study(client, date(2026, 10, 12) + timedelta(days=i), 180)
    s = client.get("/api/v1/game/summary").json()
    assert s["streak"]["current"] == 5
    assert s["streak"]["frozen_days"] == ["2026-10-19"]
    ledger = client.get("/api/v1/game/xp", params={"from": "2026-10-18", "to": "2026-10-18"}).json()["items"]
    assert [(e["source"], e["xp"]) for e in ledger] == [("week_complete", 150)]


def test_level_up_reported(client, clock):
    clock.today = date(2026, 10, 12)
    study(client, date(2026, 10, 9), 60)
    body = {"id": str(uuid.uuid4()), "studied_on": "2026-10-12", "duration_minutes": 60,
            "activity": "theory", "topic_ids": ["E01.02"]}
    delta = client.post("/api/v1/sessions", json=body).json()["game_delta"]
    assert delta["level_up"] == 2


def test_deleting_session_removes_its_xp(client):
    body = {"id": str(uuid.uuid4()), "studied_on": "2026-10-09", "duration_minutes": 40,
            "activity": "theory", "topic_ids": ["E01.02"]}
    client.post("/api/v1/sessions", json=body)
    assert client.get("/api/v1/game/summary").json()["xp_total"] == 40
    assert client.delete(f"/api/v1/sessions/{body['id']}").status_code == 204
    assert client.get("/api/v1/game/summary").json()["xp_total"] == 0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `docker compose --profile test run --rm test pytest tests/integration/test_game.py -q`
Expected: FAIL; `GET /game/summary` responde 404.

- [ ] **Step 3: Implementar e registrar**

`apps/api/app/game/router.py`:

```python
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import get_db
from app.errors import ApiError
from app.game import config as game_config
from app.game import snapshot
from app.game.snapshot import tracked
from app.models import DayOff

router = APIRouter(tags=["game"])


class DayOffIn(BaseModel):
    reason: str = Field(min_length=1, max_length=100)


@router.get("/game/summary")
def get_summary(db: Session = Depends(get_db), today: date = Depends(get_today)):
    return snapshot.summary(db, today)


@router.get("/game/xp")
def get_xp(from_: date = Query(alias="from"), to: date = Query(), db: Session = Depends(get_db),
           today: date = Depends(get_today)):
    items = snapshot.ledger(db, today, from_, to)
    return {"items": items, "total": len(items)}


@router.get("/game/config")
def get_config():
    cfg = game_config.game_config()
    return {"holiday_suggestions": cfg.get("holiday_suggestions", []), "milestones": cfg["milestones"]}


@router.get("/day-offs")
def list_day_offs(db: Session = Depends(get_db)):
    rows = db.scalars(select(DayOff).order_by(DayOff.day))
    items = [{"day": r.day, "reason": r.reason} for r in rows]
    return {"items": items, "total": len(items)}


@router.put("/day-offs/{day}")
def put_day_off(day: date, body: DayOffIn, db: Session = Depends(get_db), today: date = Depends(get_today)):
    if day.weekday() >= 5:
        raise ApiError(422, "weekend", "Fim de semana já é neutro para a sequência.")

    def action():
        row = db.get(DayOff, day) or DayOff(day=day)
        row.reason = body.reason
        db.add(row)
        return row

    row, delta = tracked(db, today, action)
    return {"day": row.day, "reason": row.reason, "game_delta": delta}


@router.delete("/day-offs/{day}", status_code=204)
def delete_day_off(day: date, db: Session = Depends(get_db), today: date = Depends(get_today)):
    def action():
        row = db.get(DayOff, day)
        if row is not None:
            db.delete(row)

    tracked(db, today, action)
    return Response(status_code=204)
```

`apps/api/app/main.py`:

```python
from app.game.router import router as game_router
```

```python
    for router in (catalog_router, planning_router, study_router, game_router):
```

- [ ] **Step 4: Rodar e ver passar**

Run: `docker compose --profile test run --rm test pytest tests/integration/test_game.py -q`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api
git commit -m "feat(api): resumo do jogo, extrato de XP e folgas"
```

---

### Task 10: Missão do dia e visão do dia

**Files:**
- Create: `apps/api/app/game/missions.py`, `apps/api/app/game/mission_router.py`
- Modify: `apps/api/app/main.py` (versão final abaixo)
- Test: `apps/api/tests/integration/test_mission.py`

**Interfaces:**
- Consumes: `domain.mission`, `planning.service.{current_plan, ensure_week, occurrences_out}`, `game.snapshot.{ledger, load_world, mission_states, tracked}`.
- Produces: `missions.{get_mission(db, day), mission_out(db, mission) -> dict, open_day(db, day, today, chosen) -> (DailyMission, created), set_item_na(db, mission_id, item_id, reason), set_checkout(db, mission_id, note), day_view(db, day, today) -> dict}`; rotas `GET /days/{day}`, `POST /days/{day}/mission` (`{occurrence_ids: []}`), `PATCH /missions/{id}/items/{item_id}` (`{na_reason}`), `PUT /missions/{id}/checkout` (`{note}`). DTO da missão: `id, date, kind, checkout_note, complete, items[{id, position, kind, ref_id, required, target, state, na_reason}]`. Visão do dia: `date, kind, in_plan, week_generated, occurrences, mission|null, xp_today`.

- [ ] **Step 1: Escrever o teste que falha**

`apps/api/tests/integration/test_mission.py`:

```python
import uuid
from datetime import date


def session_for(client, occurrence_id, minutes=60, studied_on="2026-10-09", **extra):
    body = {"id": str(uuid.uuid4()), "occurrence_id": occurrence_id, "studied_on": studied_on,
            "duration_minutes": minutes, "activity": "theory", "topic_ids": ["C02.01"],
            "complete_occurrence": True}
    body.update(extra)
    return client.post("/api/v1/sessions", json=body)


def test_get_day_does_not_write(client):
    day = client.get("/api/v1/days/2026-10-09").json()
    assert (day["week_generated"], day["mission"], day["occurrences"]) == (False, None, [])


def test_open_day_generates_week_and_is_idempotent(client):
    r = client.post("/api/v1/days/2026-10-09/mission", json={})
    assert r.status_code == 201
    kinds = [(i["kind"], i["required"]) for i in r.json()["items"]]
    assert kinds == [("block", True), ("block", True), ("block", True), ("checkout", False)]
    again = client.post("/api/v1/days/2026-10-09/mission", json={})
    assert again.status_code == 200
    assert again.json()["id"] == r.json()["id"]


def test_future_and_out_of_plan_days_rejected(client):
    assert client.post("/api/v1/days/2026-10-10/mission", json={}).status_code == 422
    assert client.post("/api/v1/days/2026-10-08/mission", json={}).status_code == 422


def test_block_registered_before_opening_day_still_counts(client):
    occ = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-05"}).json()["items"][0]
    session_for(client, occ["id"])
    mission = client.post("/api/v1/days/2026-10-09/mission", json={}).json()
    first = mission["items"][0]
    assert (first["ref_id"], first["state"]) == (occ["id"], "done")


def test_mission_completion_with_not_applicable_and_bonus(client):
    mission = client.post("/api/v1/days/2026-10-09/mission", json={}).json()
    blocks = [i for i in mission["items"] if i["kind"] == "block"]
    for item in blocks[1:]:
        r = client.patch(f"/api/v1/missions/{mission['id']}/items/{item['id']}", json={"na_reason": "indisponível"})
        assert r.json()["complete"] is False
    done = session_for(client, blocks[0]["ref_id"])
    delta = done.json()["game_delta"]
    assert delta["mission_complete"] == ["2026-10-09"]
    assert delta["xp_gained"] == 60 + 20 + 50
    checkout = client.put(f"/api/v1/missions/{mission['id']}/checkout", json={"note": "Prazos da LAI."})
    assert checkout.json()["game_delta"]["xp_gained"] == 10


def test_all_not_applicable_is_not_complete(client):
    mission = client.post("/api/v1/days/2026-10-09/mission", json={}).json()
    for item in mission["items"]:
        if item["required"]:
            last = client.patch(f"/api/v1/missions/{mission['id']}/items/{item['id']}", json={"na_reason": "x"})
    assert last.json()["complete"] is False


def test_rescheduled_block_becomes_not_applicable(client):
    mission = client.post("/api/v1/days/2026-10-09/mission", json={}).json()
    day = client.get("/api/v1/days/2026-10-09").json()
    occ = day["occurrences"][0]
    client.patch(f"/api/v1/occurrences/{occ['id']}", json={"version": occ["version"], "planned_on": "2026-10-12"})
    items = client.get("/api/v1/days/2026-10-09").json()["mission"]["items"]
    moved = next(i for i in items if i["ref_id"] == occ["id"])
    assert (moved["state"], moved["na_reason"]) == ("not_applicable", "rescheduled")


def test_free_mission_on_weekend(client, clock):
    pending = client.post("/api/v1/plans/current/weeks", json={"week_start": "2026-10-05"}).json()["items"]
    clock.today = date(2026, 10, 10)
    too_many = client.post("/api/v1/days/2026-10-10/mission",
                           json={"occurrence_ids": [o["id"] for o in pending]})
    assert too_many.status_code == 422
    r = client.post("/api/v1/days/2026-10-10/mission", json={"occurrence_ids": [pending[0]["id"]]})
    assert r.status_code == 201
    assert r.json()["kind"] == "free"
    day = client.get("/api/v1/days/2026-10-10").json()
    assert [o["id"] for o in day["occurrences"]] == [pending[0]["id"]]


def test_concurrent_open_day_returns_existing_mission(client, monkeypatch):
    from app.game import missions

    first = client.post("/api/v1/days/2026-10-09/mission", json={}).json()
    real = missions.get_mission
    calls = {"n": 0}

    def racing(db, day):
        calls["n"] += 1
        return None if calls["n"] == 1 else real(db, day)

    monkeypatch.setattr(missions, "get_mission", racing)
    r = client.post("/api/v1/days/2026-10-09/mission", json={})
    assert r.status_code == 200
    assert r.json()["id"] == first["id"]


def test_moving_session_date_uncompletes_original_mission(client, clock):
    clock.today = date(2026, 10, 12)
    mission = client.post("/api/v1/days/2026-10-09/mission", json={}).json()
    blocks = [i for i in mission["items"] if i["kind"] == "block"]
    for item in blocks[1:]:
        client.patch(f"/api/v1/missions/{mission['id']}/items/{item['id']}", json={"na_reason": "x"})
    created = session_for(client, blocks[0]["ref_id"]).json()
    assert created["game_delta"]["mission_complete"] == ["2026-10-09"]
    moved = client.patch(f"/api/v1/sessions/{created['id']}",
                         json={"version": created["version"], "studied_on": "2026-10-12"})
    assert moved.json()["game_delta"]["xp_gained"] == -50
    assert client.get("/api/v1/days/2026-10-09").json()["mission"]["complete"] is False
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `docker compose --profile test run --rm test pytest tests/integration/test_mission.py -q`
Expected: FAIL; `GET /days/2026-10-09` responde 404.

- [ ] **Step 3: Implementar o serviço da missão**

`apps/api/app/game/missions.py`:

```python
"""Missão do dia: abrir o dia, itens, check-out e visão do dia (R13)."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import mission as mission_domain
from app.domain.cycle import week_start_of
from app.errors import ApiError
from app.game.snapshot import ledger, load_world, mission_states
from app.models import DailyMission, MissionItem, Occurrence
from app.planning.service import current_plan, ensure_week, occurrences_out


def get_mission(db: Session, day: date) -> DailyMission | None:
    return db.scalar(select(DailyMission).where(DailyMission.mission_date == day))


def mission_out(db: Session, mission: DailyMission) -> dict:
    world = load_world(db)
    states = mission_states(world, mission)
    pairs = [(item.required, state) for item, state in states]
    return {
        "id": str(mission.id),
        "date": mission.mission_date,
        "kind": mission.kind,
        "checkout_note": mission.checkout_note,
        "complete": mission_domain.is_complete(pairs),
        "items": [
            {"id": str(item.id), "position": item.position, "kind": item.kind,
             "ref_id": str(item.ref_id) if item.ref_id else None, "required": item.required,
             "target": item.target, "state": state.state, "na_reason": state.reason}
            for item, state in states
        ],
    }


def _plan_day_guard(db: Session, day: date, today: date) -> None:
    plan = current_plan(db)
    if day > today:
        raise ApiError(422, "future_day", "Não é possível abrir um dia futuro.")
    if not plan.starts_on <= day <= plan.ends_on:
        raise ApiError(422, "outside_plan", "Data fora do plano de estudos.")


def open_day(db: Session, day: date, today: date, chosen: list[uuid.UUID]) -> tuple[DailyMission, bool]:
    existing = get_mission(db, day)
    if existing is not None:
        return existing, False
    _plan_day_guard(db, day, today)
    kind = mission_domain.mission_kind(day)
    if kind == "weekday":
        ensure_week(db, week_start_of(day))
        occs = list(db.scalars(select(Occurrence).where(Occurrence.planned_on == day)))
    else:
        if len(chosen) > 2:
            raise ApiError(422, "too_many_blocks", "Escolha no máximo 2 blocos na missão livre.")
        occs = []
        for occ_id in chosen:
            occ = db.get(Occurrence, occ_id)
            if occ is None or occ.status != "pending":
                raise ApiError(422, "invalid_block", "Escolha blocos pendentes.", {"occurrence_ids": str(occ_id)})
            occ.planned_on = day
            occ.version += 1
            occs.append(occ)
    refs = [mission_domain.OccRef(str(o.id), o.status, o.planned_on, o.window) for o in occs]
    question_goal = 0  # F2 passa a usar settings.daily_question_goal
    mission = DailyMission(id=uuid.uuid4(), mission_date=day, kind=kind)
    mission.items = [
        MissionItem(id=uuid.uuid4(), position=i.position, kind=i.kind,
                    ref_id=uuid.UUID(i.ref_id) if i.ref_id else None,
                    target=i.target, required=i.required, na_reason=i.na_reason)
        for i in mission_domain.build_mission(day, refs, question_goal)
    ]
    db.add(mission)
    db.flush()
    return mission, True


def set_item_na(db: Session, mission_id: uuid.UUID, item_id: uuid.UUID, reason: str | None) -> DailyMission:
    item = db.get(MissionItem, item_id)
    if item is None or item.mission_id != mission_id:
        raise ApiError(404, "not_found", "Item não encontrado.")
    item.na_reason = (reason or "").strip() or None
    db.flush()
    return db.get(DailyMission, mission_id)


def set_checkout(db: Session, mission_id: uuid.UUID, note: str) -> DailyMission:
    mission = db.get(DailyMission, mission_id)
    if mission is None:
        raise ApiError(404, "not_found", "Missão não encontrada.")
    mission.checkout_note = note.strip() or None
    db.flush()
    return mission


def day_view(db: Session, day: date, today: date) -> dict:
    plan = current_plan(db)
    mission = get_mission(db, day)
    occs = sorted(db.scalars(select(Occurrence).where(Occurrence.planned_on == day)),
                  key=lambda o: o.slot.position)
    week_generated = db.scalar(
        select(Occurrence.id).where(Occurrence.week_start == week_start_of(day)).limit(1)
    ) is not None
    xp_today = sum(e["xp"] for e in ledger(db, today, day, day))
    return {
        "date": day,
        "kind": mission_domain.mission_kind(day),
        "in_plan": plan.starts_on <= day <= plan.ends_on,
        "week_generated": week_generated,
        "occurrences": occurrences_out(db, occs),
        "mission": mission_out(db, mission) if mission else None,
        "xp_today": xp_today,
    }
```

- [ ] **Step 4: Implementar o roteador (com nova tentativa em corrida de unicidade)**

`apps/api/app/game/mission_router.py`:

```python
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import get_db
from app.game import missions as service
from app.game.snapshot import tracked

router = APIRouter(tags=["missions"])


class OpenDayIn(BaseModel):
    occurrence_ids: list[uuid.UUID] = []


class ItemPatch(BaseModel):
    na_reason: str | None = Field(default=None, max_length=200)


class CheckoutIn(BaseModel):
    note: str = Field(max_length=500)


@router.get("/days/{day}")
def get_day(day: date, db: Session = Depends(get_db), today: date = Depends(get_today)):
    return service.day_view(db, day, today)


@router.post("/days/{day}/mission")
def open_day(day: date, body: OpenDayIn, response: Response, db: Session = Depends(get_db),
             today: date = Depends(get_today)):
    def action():
        return service.open_day(db, day, today, body.occurrence_ids)

    try:
        (mission, created), delta = tracked(db, today, action)
    except IntegrityError:
        # Outra requisição (clique duplo, outro aparelho) gravou o mesmo dia/semana: a segunda tentativa encontra o registro.
        db.rollback()
        (mission, created), delta = tracked(db, today, action)
    response.status_code = 201 if created else 200
    return {**service.mission_out(db, mission), "game_delta": delta}


@router.patch("/missions/{mission_id}/items/{item_id}")
def patch_item(mission_id: uuid.UUID, item_id: uuid.UUID, body: ItemPatch, db: Session = Depends(get_db),
               today: date = Depends(get_today)):
    mission, delta = tracked(db, today, lambda: service.set_item_na(db, mission_id, item_id, body.na_reason))
    return {**service.mission_out(db, mission), "game_delta": delta}


@router.put("/missions/{mission_id}/checkout")
def put_checkout(mission_id: uuid.UUID, body: CheckoutIn, db: Session = Depends(get_db),
                 today: date = Depends(get_today)):
    mission, delta = tracked(db, today, lambda: service.set_checkout(db, mission_id, body.note))
    return {**service.mission_out(db, mission), "game_delta": delta}
```

`apps/api/app/main.py`, versão final:

```python
from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import config, errors
from app.catalog.router import router as catalog_router
from app.game.mission_router import router as mission_router
from app.game.router import router as game_router
from app.planning.router import router as planning_router
from app.study.router import router as study_router


def mount_spa(app: FastAPI) -> None:
    static = config.STATIC_DIR.resolve()
    if not (static / "index.html").is_file():
        return

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise errors.ApiError(404, "not_found", "Rota inexistente.")
        candidate = (static / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(static):
            return FileResponse(candidate)
        return FileResponse(static / "index.html")


def create_app() -> FastAPI:
    app = FastAPI(title="CGU 2026", docs_url="/api/docs", openapi_url="/api/openapi.json")
    errors.install(app)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.ALLOWED_HOSTS)
    api = APIRouter(prefix="/api/v1")

    @api.get("/health")
    def health():
        return {"status": "ok"}

    for router in (catalog_router, planning_router, study_router, game_router, mission_router):
        api.include_router(router)
    app.include_router(api)
    mount_spa(app)
    return app


app = create_app()
```

- [ ] **Step 5: Rodar toda a suíte da API**

Run: `docker compose --profile test run --rm test`
Expected: 74 passed.

- [ ] **Step 6: Commit**

```bash
git add apps/api
git commit -m "feat(api): abrir o dia, missão com não se aplica, check-out e visão do dia"
```

---

### Task 11: Frontend — base, HUD e tela Hoje

**Files:**
- Create: `apps/web/` (scaffold Vite), `apps/web/{index.html,vite.config.ts}`, `src/{main.tsx,index.css}`, `src/test/setup.ts`, `src/app/{App,Hud}.tsx`, `src/shared/api/{client,types,hooks}.ts`, `src/shared/format.ts`, `src/shared/ui/GameToast.tsx`, `src/features/today/{TodayPage,SessionForm,MissionRing}.tsx`
- Test: `src/shared/format.test.ts`, `src/features/today/SessionForm.test.tsx`

**Interfaces:**
- Consumes: contratos HTTP das Tarefas 7–10 (tipos espelhados em `types.ts`).
- Produces: `api<T>(path, method?, body?)`, `ApiError(status, code, message, fields)`, `NetworkError`; hooks `useSummary, useDay, useOccurrences, useSubjects, useDayOffs, useCreateSession, useOpenDay, useGenerateWeek, usePatchOccurrence, useSetItemNa, useCheckout, usePutDayOff, useDeleteDayOff, usePutProgress`; `useGameToast()`; `WINDOW_LABEL, PURPOSE_LABEL, XP_SOURCE_LABEL, addDays, mondayOf, formatDay`.

- [ ] **Step 1: Criar o projeto e instalar dependências**

```bash
npm create vite@latest apps/web -- --template react-ts --no-interactive
cd apps/web
npm install
npm install react-router-dom @tanstack/react-query @fontsource/chakra-petch @fontsource/inter @fontsource/jetbrains-mono
npm install -D tailwindcss @tailwindcss/vite vitest jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom
rm -rf src/App.css src/App.tsx src/assets public/*
mkdir -p src/app src/shared/api src/shared/ui src/features/today src/features/cycle src/features/catalog src/features/settings src/test public/icons
npm pkg set scripts.test="vitest run"
```

- [ ] **Step 2: Configuração, tema e setup de testes**

`apps/web/vite.config.ts`:

```ts
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': 'http://127.0.0.1:8080' } },
  test: { environment: 'jsdom', setupFiles: ['./src/test/setup.ts'] },
})
```

`apps/web/index.html`:

```html
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#0B1220" />
    <link rel="manifest" href="/manifest.webmanifest" />
    <link rel="icon" type="image/png" href="/icons/icon-192.png" />
    <link rel="apple-touch-icon" href="/icons/icon-192.png" />
    <title>CGU 2026</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`apps/web/src/index.css`:

```css
@import "tailwindcss";

@theme {
  --color-bg: #0b1220;
  --color-surface: #121a2b;
  --color-surface-2: #1a2438;
  --color-border: #26324a;
  --color-text: #e6eaf2;
  --color-muted: #9aa6bd;
  --color-primary: #3b82f6;
  --color-xp: #facc15;
  --color-streak: #fb923c;
  --color-success: #22c55e;
  --color-danger: #f87171;
  --color-p1: #60a5fa;
  --color-p2: #a78bfa;
  --color-p3: #34d399;
  --font-display: "Chakra Petch", system-ui, sans-serif;
  --font-sans: "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
}

html {
  color-scheme: dark;
}

body {
  @apply bg-bg text-text font-sans antialiased;
  font-size: 16px;
}

:focus-visible {
  outline: 2px solid var(--color-primary);
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

`apps/web/src/test/setup.ts`:

```ts
import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => cleanup())
```

- [ ] **Step 3: Escrever os testes que falham**

`apps/web/src/shared/format.test.ts`:

```ts
import { describe, expect, it } from 'vitest'

import { addDays, mondayOf } from './format'

describe('datas civis', () => {
  it('calcula a segunda-feira sem depender do fuso do navegador', () => {
    expect(mondayOf('2026-10-09')).toBe('2026-10-05')
    expect(mondayOf('2026-10-12')).toBe('2026-10-12')
    expect(mondayOf('2026-10-11')).toBe('2026-10-05')
  })
  it('soma dias atravessando o mês', () => {
    expect(addDays('2026-10-30', 3)).toBe('2026-11-02')
  })
})
```

`apps/web/src/features/today/SessionForm.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Occurrence, Subject } from '../../shared/api/types'
import { GameToastProvider } from '../../shared/ui/GameToast'
import { SessionForm } from './SessionForm'

const subjects: Subject[] = [
  { id: 'C02', paper: 'P2', title: 'Transparência', topics: [{ id: 'C02.01', title: 'Acesso à informação', source_ref: '', progress: null }] },
]

const occurrence: Occurrence = {
  id: 'occ-1', version: 1, week_start: '2026-10-05', planned_on: '2026-10-09', window: 'before', status: 'pending',
  skip_reason: null, actual_minutes: 0, completed_on: null, suggested_topic_id: 'C02.01',
  slot: { code: 'S13', title: 'Complementares e revisão', purpose: 'complementary', activity: 'theory', minutes: 60,
    selection_mode: 'alternate_subjects', candidate_topic_ids: ['C02.01'] },
}

function renderForm(onSaved = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <GameToastProvider>
        <SessionForm occurrence={occurrence} today="2026-10-09" subjects={subjects} onSaved={onSaved} onCancel={vi.fn()} />
      </GameToastProvider>
    </QueryClientProvider>,
  )
  return onSaved
}

afterEach(() => vi.unstubAllGlobals())

describe('SessionForm', () => {
  it('mantém os dados após falha de rede e reenvia com o mesmo id', async () => {
    const delta = { xp_gained: 80, entries: [], level_up: null, mission_complete: [], streak: 1 }
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(new Response(JSON.stringify({ game_delta: delta }), { status: 201 }))
    vi.stubGlobal('fetch', fetchMock)
    const onSaved = renderForm()
    const user = userEvent.setup()

    const minutes = screen.getByLabelText('Minutos')
    await user.clear(minutes)
    await user.type(minutes, '45')
    await user.click(screen.getByRole('button', { name: 'Registrar sessão' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Sem conexão')
    expect(screen.getByLabelText('Minutos')).toHaveValue(45)
    expect(onSaved).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Registrar sessão' }))
    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    const [first, second] = fetchMock.mock.calls.map((c) => JSON.parse(c[1].body))
    expect(second.id).toBe(first.id)
    expect(second).toMatchObject({ duration_minutes: 45, topic_ids: ['C02.01'], complete_occurrence: true, occurrence_id: 'occ-1' })
  })

  it('mostra erros de campo do servidor', async () => {
    const body = { error: { code: 'invalid_input', message: 'Revise os campos destacados.', fields: { studied_on: 'Data futura.' } } }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 422 })))
    renderForm()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Registrar sessão' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('studied_on: Data futura.')
  })
})
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `cd apps/web && npm test`
Expected: FAIL com `Failed to resolve import "./format"` e `"./SessionForm"`.

- [ ] **Step 5: Implementar a camada de API e utilitários**

`apps/web/src/shared/api/client.ts`:

```ts
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: Record<string, string>

  constructor(status: number, code: string, message: string, fields: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.code = code
    this.fields = fields
  }
}

export class NetworkError extends Error {}

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export async function api<T>(path: string, method: Method = 'GET', body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(`/api/v1${path}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new NetworkError('Sem conexão com o servidor. Os dados só serão salvos após confirmação do servidor.')
  }
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const e = data.error ?? {}
    throw new ApiError(res.status, e.code ?? 'unknown', e.message ?? 'Erro inesperado.', e.fields ?? {})
  }
  return data as T
}
```

`apps/web/src/shared/api/types.ts`:

```ts
export type Window = 'before' | 'middle' | 'after'
export type OccurrenceStatus = 'pending' | 'completed' | 'skipped'
export type Activity = 'theory' | 'questions' | 'review' | 'essay'
export type EssayKind = 'complementary' | 'technical_case'

export interface XpDeltaEntry { source: string; ref_id: string; date: string; xp: number }

export interface GameDelta {
  xp_gained: number
  entries: XpDeltaEntry[]
  level_up: number | null
  mission_complete: string[]
  streak: number
}

export interface Summary {
  today: string
  exam_date: string
  days_to_exam: number
  xp_total: number
  level: number
  title: string
  xp_into_level: number
  xp_for_next: number
  streak: {
    current: number
    best: number
    freezes_available: number
    frozen_days: string[]
    at_stake_today: boolean
    minutes_today: number
    min_minutes: number
  }
  holiday_suggestion: { date: string; label: string } | null
}

export interface Slot {
  code: string
  title: string
  purpose: 'specific' | 'basic' | 'complementary' | 'essay'
  activity: Activity
  minutes: number
  selection_mode: string
  candidate_topic_ids: string[]
}

export interface Occurrence {
  id: string
  version: number
  week_start: string
  planned_on: string
  window: Window
  status: OccurrenceStatus
  skip_reason: string | null
  actual_minutes: number
  completed_on: string | null
  slot: Slot
  suggested_topic_id: string | null
}

export interface MissionItem {
  id: string
  position: number
  kind: 'block' | 'review' | 'questions' | 'checkout'
  ref_id: string | null
  required: boolean
  target: number | null
  state: 'pending' | 'done' | 'not_applicable'
  na_reason: string | null
}

export interface Mission {
  id: string
  date: string
  kind: 'weekday' | 'free'
  checkout_note: string | null
  complete: boolean
  items: MissionItem[]
}

export interface DayView {
  date: string
  kind: 'weekday' | 'free'
  in_plan: boolean
  week_generated: boolean
  occurrences: Occurrence[]
  mission: Mission | null
  xp_today: number
}

export interface Topic {
  id: string
  title: string
  source_ref: string
  progress: { status: string; declared_on: string; version: number } | null
}

export interface Subject { id: string; paper: 'P1' | 'P2' | 'P3'; title: string; topics: Topic[] }

export interface SessionInput {
  id: string
  occurrence_id: string | null
  studied_on: string
  duration_minutes: number
  activity: Activity
  essay_kind: EssayKind | null
  topic_ids: string[]
  notes: string
  complete_occurrence: boolean
}

export interface WithDelta { game_delta: GameDelta }

export interface ListResponse<T> { items: T[]; total: number }

export interface DayOff { day: string; reason: string }
```

`apps/web/src/shared/api/hooks.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useGameToast } from '../ui/GameToast'
import { api } from './client'
import type {
  DayOff, DayView, ListResponse, Mission, Occurrence, SessionInput, Subject, Summary, WithDelta,
} from './types'

export const useSummary = () => useQuery({ queryKey: ['summary'], queryFn: () => api<Summary>('/game/summary') })

export const useDay = (day: string | undefined) =>
  useQuery({ queryKey: ['day', day], queryFn: () => api<DayView>(`/days/${day}`), enabled: !!day })

export const useOccurrences = (from: string, to: string) =>
  useQuery({
    queryKey: ['occurrences', from, to],
    queryFn: () => api<ListResponse<Occurrence>>(`/occurrences?from=${from}&to=${to}`),
  })

export const useSubjects = () =>
  useQuery({ queryKey: ['subjects'], queryFn: () => api<ListResponse<Subject>>('/subjects'), staleTime: Infinity })

export const useDayOffs = () => useQuery({ queryKey: ['day-offs'], queryFn: () => api<ListResponse<DayOff>>('/day-offs') })

/** Mutação que mostra o efeito no jogo e atualiza HUD, dia e ciclo. */
function useGameMutation<V, R extends Partial<WithDelta> | void>(fn: (v: V) => Promise<R>) {
  const qc = useQueryClient()
  const toast = useGameToast()
  return useMutation({
    mutationFn: fn,
    onSuccess: (result) => {
      if (result && result.game_delta) toast(result.game_delta)
      for (const key of ['summary', 'day', 'occurrences', 'day-offs']) qc.invalidateQueries({ queryKey: [key] })
    },
  })
}

export const useCreateSession = () =>
  useGameMutation((s: SessionInput) => api<WithDelta>('/sessions', 'POST', s))

export const useOpenDay = () =>
  useGameMutation((v: { day: string; occurrence_ids?: string[] }) =>
    api<Mission & WithDelta>(`/days/${v.day}/mission`, 'POST', { occurrence_ids: v.occurrence_ids ?? [] }))

export const useGenerateWeek = () =>
  useGameMutation((week_start: string) => api<WithDelta>('/plans/current/weeks', 'POST', { week_start }))

export const usePatchOccurrence = () =>
  useGameMutation((v: { id: string; body: Record<string, unknown> }) =>
    api<Occurrence & WithDelta>(`/occurrences/${v.id}`, 'PATCH', v.body))

export const useSetItemNa = () =>
  useGameMutation((v: { missionId: string; itemId: string; na_reason: string | null }) =>
    api<Mission & WithDelta>(`/missions/${v.missionId}/items/${v.itemId}`, 'PATCH', { na_reason: v.na_reason }))

export const useCheckout = () =>
  useGameMutation((v: { missionId: string; note: string }) =>
    api<Mission & WithDelta>(`/missions/${v.missionId}/checkout`, 'PUT', { note: v.note }))

export const usePutDayOff = () =>
  useGameMutation((v: DayOff) => api<WithDelta>(`/day-offs/${v.day}`, 'PUT', { reason: v.reason }))

export const useDeleteDayOff = () => useGameMutation((day: string) => api<void>(`/day-offs/${day}`, 'DELETE'))

export const usePutProgress = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (v: { topicId: string; status: string; version?: number }) =>
      api(`/topics/${v.topicId}/progress`, 'PUT', { status: v.status, version: v.version }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subjects'] }),
  })
}
```

`apps/web/src/shared/format.ts`:

```ts
import type { Window } from './api/types'

export const WINDOW_LABEL: Record<Window, string> = { before: 'Antes', middle: 'Intermediário', after: 'Depois' }

export const PURPOSE_LABEL = {
  specific: 'Específicos',
  basic: 'Básicos',
  complementary: 'Complementares',
  essay: 'Discursiva',
} as const

export const XP_SOURCE_LABEL: Record<string, string> = {
  session_minutes: 'minutos de estudo',
  block_completed: 'bloco concluído',
  mission_complete: 'missão completa',
  mission_optional: 'item bônus',
  weekend_day: 'dia extra',
  week_complete: 'semana completa',
}

export function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

export function mondayOf(iso: string): string {
  const d = new Date(`${iso}T12:00:00Z`)
  return addDays(iso, -((d.getUTCDay() + 6) % 7))
}

export function formatDay(iso: string): string {
  return new Date(`${iso}T12:00:00Z`).toLocaleDateString('pt-BR', {
    weekday: 'short', day: '2-digit', month: '2-digit', timeZone: 'UTC',
  })
}
```

`apps/web/src/shared/ui/GameToast.tsx`:

```tsx
import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'

import type { GameDelta } from '../api/types'
import { XP_SOURCE_LABEL } from '../format'

type Show = (delta: GameDelta) => void

const ToastContext = createContext<Show>(() => {})

export const useGameToast = () => useContext(ToastContext)

interface Toast { id: number; lines: string[]; levelUp: number | null }

export function GameToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const show = useCallback<Show>((delta) => {
    const gains = delta.entries.filter((e) => e.xp > 0)
    if (gains.length === 0 && !delta.level_up) return
    const id = Date.now() + Math.random()
    const lines = gains.map((e) => `+${e.xp} XP · ${XP_SOURCE_LABEL[e.source] ?? e.source}`)
    setToasts((t) => [...t, { id, lines, levelUp: delta.level_up }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000)
  }, [])
  return (
    <ToastContext.Provider value={show}>
      {children}
      <div aria-live="polite" className="fixed bottom-20 right-4 z-50 flex flex-col gap-2 md:bottom-4">
        {toasts.map((t) => (
          <div key={t.id} className="rounded-lg border border-xp/40 bg-surface-2 px-4 py-3 shadow-lg">
            {t.levelUp && <p className="font-display text-lg font-bold text-xp">Nível {t.levelUp}!</p>}
            {t.lines.map((line) => (
              <p key={line} className="num text-sm text-xp">{line}</p>
            ))}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
```

- [ ] **Step 6: Implementar a tela Hoje**

`apps/web/src/features/today/SessionForm.tsx`:

```tsx
import { useState, type FormEvent } from 'react'

import { ApiError } from '../../shared/api/client'
import { useCreateSession } from '../../shared/api/hooks'
import type { Activity, EssayKind, Occurrence, Subject } from '../../shared/api/types'

interface Props {
  occurrence: Occurrence | null
  today: string
  subjects: Subject[]
  onSaved: () => void
  onCancel: () => void
}

const ACTIVITY_LABEL: Record<Activity, string> = {
  theory: 'Teoria', questions: 'Questões', review: 'Revisão', essay: 'Discursiva',
}

function defaultEssayKind(o: Occurrence | null): EssayKind {
  return o?.slot.selection_mode === 'technical_case' ? 'technical_case' : 'complementary'
}

export function SessionForm({ occurrence, today, subjects, onSaved, onCancel }: Props) {
  const [id] = useState(() => crypto.randomUUID())
  const [activity, setActivity] = useState<Activity>(occurrence?.slot.activity ?? 'theory')
  const [topicId, setTopicId] = useState(occurrence?.suggested_topic_id ?? '')
  const [essayKind, setEssayKind] = useState<EssayKind>(defaultEssayKind(occurrence))
  const [minutes, setMinutes] = useState(String(occurrence?.slot.minutes ?? 60))
  const [studiedOn, setStudiedOn] = useState(today)
  const [notes, setNotes] = useState('')
  const [complete, setComplete] = useState(occurrence !== null)
  const [error, setError] = useState<{ message: string; fields: Record<string, string> } | null>(null)
  const create = useCreateSession()
  const isEssay = activity === 'essay'

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await create.mutateAsync({
        id,
        occurrence_id: occurrence?.id ?? null,
        studied_on: studiedOn,
        duration_minutes: Number(minutes),
        activity,
        essay_kind: isEssay ? essayKind : null,
        topic_ids: topicId ? [topicId] : [],
        notes,
        complete_occurrence: complete,
      })
      onSaved()
    } catch (err) {
      const fields = err instanceof ApiError ? err.fields : {}
      setError({ message: err instanceof Error ? err.message : 'Erro inesperado.', fields })
    }
  }

  const input = 'mt-1 w-full rounded-md border border-border bg-surface-2 px-3 py-2'
  return (
    <form onSubmit={submit} className="space-y-3 rounded-lg border border-border bg-surface p-4" aria-label="Registrar sessão">
      <h3 className="font-display text-lg font-semibold">
        {occurrence ? `${occurrence.slot.code} · ${occurrence.slot.title}` : 'Sessão avulsa'}
      </h3>
      {!occurrence && (
        <label className="block text-sm">Atividade
          <select className={input} value={activity} onChange={(e) => setActivity(e.target.value as Activity)}>
            {Object.entries(ACTIVITY_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
      )}
      {isEssay && (
        <label className="block text-sm">Tipo de discursiva
          <select className={input} value={essayKind} onChange={(e) => setEssayKind(e.target.value as EssayKind)}>
            <option value="complementary">Complementar (até 30 linhas)</option>
            <option value="technical_case">Situação-problema de TI (até 60 linhas)</option>
          </select>
        </label>
      )}
      <label className="block text-sm">Tópico {isEssay && '(opcional)'}
        <select className={input} value={topicId} onChange={(e) => setTopicId(e.target.value)} required={!isEssay}>
          <option value="">Selecione…</option>
          {subjects.map((s) => (
            <optgroup key={s.id} label={`${s.paper} · ${s.id} ${s.title}`}>
              {s.topics.map((t) => <option key={t.id} value={t.id}>{t.id} {t.title}</option>)}
            </optgroup>
          ))}
        </select>
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className="block text-sm">Minutos
          <input className={`${input} num`} type="number" inputMode="numeric" min={1} max={720} required
            value={minutes} onChange={(e) => setMinutes(e.target.value)} />
        </label>
        <label className="block text-sm">Data
          <input className={input} type="date" max={today} required value={studiedOn}
            onChange={(e) => setStudiedOn(e.target.value)} />
        </label>
      </div>
      <label className="block text-sm">Observação
        <textarea className={input} rows={2} maxLength={2000} value={notes} onChange={(e) => setNotes(e.target.value)} />
      </label>
      {occurrence && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={complete} onChange={(e) => setComplete(e.target.checked)} />
          Concluir o bloco
        </label>
      )}
      {error && (
        <div role="alert" className="rounded-md border border-danger/50 p-3 text-sm text-danger">
          <p>{error.message}</p>
          {Object.entries(error.fields).map(([f, m]) => <p key={f}>{f}: {m}</p>)}
        </div>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={create.isPending}
          className="rounded-md bg-primary px-4 py-2 font-semibold text-white disabled:opacity-60">
          {create.isPending ? 'Salvando…' : 'Registrar sessão'}
        </button>
        <button type="button" onClick={onCancel} className="rounded-md px-4 py-2 text-muted">Cancelar</button>
      </div>
    </form>
  )
}
```

`apps/web/src/features/today/MissionRing.tsx`:

```tsx
export function MissionRing({ done, total }: { done: number; total: number }) {
  const r = 28
  const c = 2 * Math.PI * r
  const pct = total === 0 ? 0 : done / total
  return (
    <svg width="72" height="72" viewBox="0 0 72 72" role="img" aria-label={`Missão: ${done} de ${total} obrigatórios`}>
      <circle cx="36" cy="36" r={r} fill="none" stroke="var(--color-surface-2)" strokeWidth="8" />
      <circle cx="36" cy="36" r={r} fill="none" stroke="var(--color-xp)" strokeWidth="8" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - pct)} transform="rotate(-90 36 36)"
        className="transition-all duration-300" />
      <text x="36" y="41" textAnchor="middle" className="num" fill="var(--color-text)" fontSize="14">
        {done}/{total}
      </text>
    </svg>
  )
}
```

`apps/web/src/features/today/TodayPage.tsx`:

```tsx
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { useCheckout, useDay, useOpenDay, usePutDayOff, useSetItemNa, useSubjects, useSummary } from '../../shared/api/hooks'
import type { DayView, MissionItem, Occurrence } from '../../shared/api/types'
import { WINDOW_LABEL } from '../../shared/format'
import { MissionRing } from './MissionRing'
import { SessionForm } from './SessionForm'

const STATE_LABEL = { pending: 'Pendente', done: '✓ Feito', not_applicable: '— Não se aplica' } as const

export function TodayPage() {
  const summary = useSummary()
  const today = summary.data?.today
  const day = useDay(today)
  const subjects = useSubjects()
  const [form, setForm] = useState<{ occurrence: Occurrence | null } | null>(null)

  if (!today || !day.data) return <p className="text-muted" aria-busy="true">Carregando…</p>
  const view = day.data

  return (
    <div className="space-y-4">
      <HolidayBanner />
      <StreakHint />
      {form ? (
        <SessionForm occurrence={form.occurrence} today={today} subjects={subjects.data?.items ?? []}
          onSaved={() => setForm(null)} onCancel={() => setForm(null)} />
      ) : (
        <>
          {view.mission ? (
            <MissionCard view={view} onRegister={(o) => setForm({ occurrence: o })} />
          ) : (
            <OpenDayCard view={view} />
          )}
          <button onClick={() => setForm({ occurrence: null })}
            className="w-full rounded-md border border-border px-4 py-2 text-sm text-muted hover:text-text">
            + Sessão avulsa
          </button>
        </>
      )}
    </div>
  )
}

function OpenDayCard({ view }: { view: DayView }) {
  const open = useOpenDay()
  if (!view.in_plan) return <p className="text-muted">Fora do período do plano.</p>
  const free = view.kind === 'free'
  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      <h2 className="font-display text-xl font-bold">{free ? 'Fim de semana' : 'Missão de hoje'}</h2>
      <p className="mt-1 text-sm text-muted">
        {free
          ? 'Sem ciclo planejado. Abra uma missão livre se quiser estudar; nada é cobrado.'
          : view.week_generated
            ? `${view.occurrences.length} blocos planejados para hoje.`
            : 'A semana ainda não foi gerada; abrir o dia também gera a semana.'}
      </p>
      <button onClick={() => open.mutate({ day: view.date })} disabled={open.isPending}
        className="mt-3 rounded-md bg-primary px-4 py-2 font-display font-semibold text-white">
        {free ? 'Abrir missão livre' : 'Abrir o dia'}
      </button>
      {open.error && <p role="alert" className="mt-2 text-sm text-danger">{open.error.message}</p>}
    </section>
  )
}

function MissionCard({ view, onRegister }: { view: DayView; onRegister: (o: Occurrence) => void }) {
  const mission = view.mission!
  const required = mission.items.filter((i) => i.required)
  const done = required.filter((i) => i.state !== 'pending').length
  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-center gap-4">
        <MissionRing done={done} total={required.length} />
        <div>
          <h2 className="font-display text-xl font-bold">
            {mission.complete ? 'Missão cumprida' : mission.kind === 'free' ? 'Missão livre' : 'Missão de hoje'}
          </h2>
          <p className="num text-sm text-xp">+{view.xp_today} XP hoje</p>
        </div>
      </div>
      <ul className="mt-4 space-y-2">
        {mission.items.map((item) => (
          <MissionRow key={item.id} item={item} missionId={mission.id} view={view} onRegister={onRegister} />
        ))}
      </ul>
    </section>
  )
}

function MissionRow({ item, missionId, view, onRegister }: {
  item: MissionItem; missionId: string; view: DayView; onRegister: (o: Occurrence) => void
}) {
  const setNa = useSetItemNa()
  if (item.kind === 'checkout') return <CheckoutRow missionId={missionId} item={item} note={view.mission!.checkout_note} />
  const occ = view.occurrences.find((o) => o.id === item.ref_id)
  return (
    <li className="flex flex-wrap items-center gap-2 rounded-md bg-surface-2 p-3">
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{occ ? `${WINDOW_LABEL[occ.window]} · ${occ.slot.title}` : 'Bloco remanejado'}</p>
        <p className="text-xs text-muted">{STATE_LABEL[item.state]}{item.na_reason ? ` (${item.na_reason})` : ''}</p>
      </div>
      {item.state === 'pending' && occ && (
        <>
          <button onClick={() => onRegister(occ)} className="rounded-md bg-primary px-3 py-1 text-sm text-white">
            Registrar sessão
          </button>
          <button onClick={() => setNa.mutate({ missionId, itemId: item.id, na_reason: 'Não se aplica hoje' })}
            className="rounded-md px-3 py-1 text-sm text-muted">Não se aplica hoje</button>
          <Link to="/ciclo" className="px-3 py-1 text-sm text-primary">Remanejar</Link>
        </>
      )}
      {item.na_reason && item.na_reason !== 'rescheduled' && item.na_reason !== 'skipped' && (
        <button onClick={() => setNa.mutate({ missionId, itemId: item.id, na_reason: null })}
          className="px-3 py-1 text-sm text-muted">Desfazer</button>
      )}
    </li>
  )
}

function CheckoutRow({ missionId, item, note }: { missionId: string; item: MissionItem; note: string | null }) {
  const [text, setText] = useState(note ?? '')
  const save = useCheckout()
  return (
    <li className="rounded-md bg-surface-2 p-3">
      <label className="block text-sm font-semibold">Check-out: o que ficou difícil hoje? <span className="text-xp">(bônus)</span>
        <textarea className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 font-normal" rows={2}
          maxLength={500} value={text} onChange={(e) => setText(e.target.value)} />
      </label>
      <button onClick={() => save.mutate({ missionId, note: text })}
        className="mt-2 rounded-md bg-primary px-3 py-1 text-sm text-white">
        {item.state === 'done' ? 'Atualizar' : 'Salvar check-out'}
      </button>
    </li>
  )
}

function StreakHint() {
  const { data } = useSummary()
  if (!data?.streak.at_stake_today) return null
  const left = data.streak.min_minutes - data.streak.minutes_today
  return <p className="text-sm text-streak">Hoje ainda conta: faltam <span className="num">{left}</span> min para manter a sequência.</p>
}

function HolidayBanner() {
  const { data } = useSummary()
  const put = usePutDayOff()
  const h = data?.holiday_suggestion
  if (!h) return null
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-md border border-border bg-surface p-3 text-sm">
      <span className="flex-1">{h.date === data!.today ? 'Hoje' : 'Amanhã'} é feriado ({h.label}). Marcar como folga?</span>
      <button onClick={() => put.mutate({ day: h.date, reason: h.label })} className="rounded-md bg-surface-2 px-3 py-1">
        Marcar folga
      </button>
    </div>
  )
}
```

- [ ] **Step 7: HUD, layout e entrada**

`apps/web/src/app/Hud.tsx`:

```tsx
import { useSummary } from '../shared/api/hooks'

export function Hud() {
  const { data } = useSummary()
  if (!data) return <div className="h-14 border-b border-border" aria-busy="true" />
  const pct = Math.min(100, Math.round((data.xp_into_level / data.xp_for_next) * 100))
  const s = data.streak
  return (
    <header className="sticky top-0 z-40 flex items-center gap-4 border-b border-border bg-bg/95 px-4 py-2 backdrop-blur">
      <div className="min-w-0 flex-1">
        <p className="font-display text-sm font-semibold">
          Nv <span className="num">{data.level}</span> · {data.title}
        </p>
        <div className="mt-1 h-2 rounded-full bg-surface-2" role="progressbar" aria-label="XP do nível"
          aria-valuemin={0} aria-valuemax={data.xp_for_next} aria-valuenow={data.xp_into_level}>
          <div className="h-2 rounded-full bg-xp transition-all duration-300" style={{ width: `${pct}%` }} />
        </div>
      </div>
      <p className="num text-sm text-streak" title={`Recorde ${s.best}`}>
        🔥 {s.current}
        {s.freezes_available > 0 && <span className="ml-1 text-primary">❄{s.freezes_available}</span>}
        <span className="sr-only"> dias de sequência</span>
      </p>
      <p className="num font-display text-sm font-bold text-xp">D-{data.days_to_exam}</p>
    </header>
  )
}
```

`apps/web/src/app/App.tsx` (só Hoje por enquanto; a Tarefa 12 substitui o arquivo):

```tsx
import { NavLink, Route, Routes } from 'react-router-dom'

import { TodayPage } from '../features/today/TodayPage'
import { Hud } from './Hud'

const LINKS = [
  { to: '/', label: 'Hoje' },
]

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 font-display text-sm font-semibold ${isActive ? 'bg-surface-2 text-xp' : 'text-muted hover:text-text'}`

export function App() {
  return (
    <div className="md:flex">
      <nav aria-label="Principal" className="fixed inset-x-0 bottom-0 z-40 flex justify-around border-t border-border bg-surface
        md:static md:h-screen md:w-48 md:flex-col md:justify-start md:gap-1 md:border-r md:border-t-0 md:p-4">
        <p className="hidden pb-4 font-display text-lg font-bold text-xp md:block">CGU 2026</p>
        {LINKS.map((l) => <NavLink key={l.to} to={l.to} end className={linkClass}>{l.label}</NavLink>)}
      </nav>
      <div className="min-h-screen flex-1 pb-20 md:pb-0">
        <Hud />
        <main className="mx-auto max-w-3xl p-4">
          <Routes>
            <Route path="/" element={<TodayPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
```

`apps/web/src/main.tsx`:

```tsx
import '@fontsource/chakra-petch/500.css'
import '@fontsource/chakra-petch/700.css'
import '@fontsource/inter/400.css'
import '@fontsource/inter/600.css'
import '@fontsource/jetbrains-mono/400.css'
import './index.css'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import { App } from './app/App'
import { GameToastProvider } from './shared/ui/GameToast'

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: true } } })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <GameToastProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </GameToastProvider>
    </QueryClientProvider>
  </StrictMode>,
)
```

- [ ] **Step 8: Rodar testes e build**

Run: `cd apps/web && npm test && npm run build`
Expected: `Tests 4 passed`; `✓ built`.

- [ ] **Step 9: Commit**

```bash
git add apps/web
git commit -m "feat(web): tema escuro, HUD, tela Hoje com missão e formulário de sessão"
```

---

### Task 12: Frontend — Ciclo, Edital, Configurações e PWA

**Files:**
- Create: `src/features/cycle/CyclePage.tsx`, `src/features/catalog/CatalogPage.tsx`, `src/features/settings/SettingsPage.tsx`, `public/manifest.webmanifest`, `scripts/make_icons.py`, `public/icons/icon-{192,512}.png`
- Modify: `src/app/App.tsx` (substituir pela versão final)

**Interfaces:**
- Consumes: hooks da Tarefa 11.
- Produces: rotas `/ciclo`, `/edital`, `/config`; manifest instalável.

- [ ] **Step 1: Páginas**

`apps/web/src/features/cycle/CyclePage.tsx`:

```tsx
import { useState } from 'react'

import { useGenerateWeek, useOccurrences, usePatchOccurrence, useSummary } from '../../shared/api/hooks'
import type { Occurrence, Window } from '../../shared/api/types'
import { addDays, formatDay, mondayOf, PURPOSE_LABEL, WINDOW_LABEL } from '../../shared/format'

export function CyclePage() {
  const summary = useSummary()
  const [offset, setOffset] = useState(0)
  if (!summary.data) return <p className="text-muted" aria-busy="true">Carregando…</p>
  const weekStart = addDays(mondayOf(summary.data.today), offset * 7)
  return <Week weekStart={weekStart} onMove={(d) => setOffset((o) => o + d)} />
}

function Week({ weekStart, onMove }: { weekStart: string; onMove: (delta: number) => void }) {
  const weekEnd = addDays(weekStart, 6)
  const { data } = useOccurrences(weekStart, weekEnd)
  const generate = useGenerateWeek()
  const byDay = new Map<string, Occurrence[]>()
  for (const o of data?.items ?? []) byDay.set(o.planned_on, [...(byDay.get(o.planned_on) ?? []), o])
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button onClick={() => onMove(-1)} className="px-3 py-2 text-primary" aria-label="Semana anterior">←</button>
        <h1 className="font-display text-lg font-bold">Semana de {formatDay(weekStart)}</h1>
        <button onClick={() => onMove(1)} className="px-3 py-2 text-primary" aria-label="Próxima semana">→</button>
      </div>
      {data && data.items.length === 0 && (
        <div className="rounded-lg border border-border bg-surface p-4">
          <p className="text-sm text-muted">Semana ainda não gerada.</p>
          <button onClick={() => generate.mutate(weekStart)} className="mt-2 rounded-md bg-primary px-4 py-2 text-white">
            Gerar semana
          </button>
          {generate.error && <p role="alert" className="mt-2 text-sm text-danger">{generate.error.message}</p>}
        </div>
      )}
      {[...byDay.entries()].map(([day, occs]) => (
        <section key={day}>
          <h2 className="mb-2 font-display text-sm font-semibold uppercase text-muted">{formatDay(day)}</h2>
          <ul className="space-y-2">{occs.map((o) => <OccurrenceRow key={o.id} occ={o} />)}</ul>
        </section>
      ))}
    </div>
  )
}

function OccurrenceRow({ occ }: { occ: Occurrence }) {
  const patch = usePatchOccurrence()
  const [moving, setMoving] = useState(false)
  const [date, setDate] = useState(occ.planned_on)
  const [window, setWindow] = useState<Window>(occ.window)
  const send = (body: Record<string, unknown>) => patch.mutate({ id: occ.id, body: { version: occ.version, ...body } })
  return (
    <li className="rounded-md bg-surface p-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{WINDOW_LABEL[occ.window]} · {occ.slot.title}</p>
          <p className="text-xs text-muted">
            {PURPOSE_LABEL[occ.slot.purpose]} · <span className="num">{occ.actual_minutes}/{occ.slot.minutes}</span> min ·{' '}
            {occ.status === 'completed' ? '✓ concluído' : occ.status === 'skipped' ? `— dispensado${occ.skip_reason ? ` (${occ.skip_reason})` : ''}` : 'pendente'}
          </p>
        </div>
        {occ.status === 'pending' && (
          <>
            <button onClick={() => setMoving((m) => !m)} className="px-2 py-1 text-sm text-primary">Remanejar bloco</button>
            <button onClick={() => send({ status: 'skipped', skip_reason: prompt('Motivo (opcional)') ?? '' })}
              className="px-2 py-1 text-sm text-muted">Dispensar</button>
            {occ.actual_minutes > 0 && (
              <button onClick={() => send({ status: 'completed' })} className="px-2 py-1 text-sm text-success">Concluir</button>
            )}
          </>
        )}
        {occ.status !== 'pending' && (
          <button onClick={() => confirm('Reabrir este bloco? As sessões continuam registradas.') && send({ status: 'pending' })}
            className="px-2 py-1 text-sm text-muted">Reabrir</button>
        )}
      </div>
      {moving && (
        <div className="mt-2 flex flex-wrap items-end gap-2">
          <label className="text-sm">Data
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
              className="ml-1 rounded-md border border-border bg-surface-2 px-2 py-1" />
          </label>
          <label className="text-sm">Janela
            <select value={window} onChange={(e) => setWindow(e.target.value as Window)}
              className="ml-1 rounded-md border border-border bg-surface-2 px-2 py-1">
              {Object.entries(WINDOW_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <button onClick={() => { send({ planned_on: date, window }); setMoving(false) }}
            className="rounded-md bg-primary px-3 py-1 text-sm text-white">Salvar</button>
        </div>
      )}
      {patch.error && <p role="alert" className="mt-1 text-sm text-danger">{patch.error.message}</p>}
    </li>
  )
}
```

`apps/web/src/features/catalog/CatalogPage.tsx`:

```tsx
import { usePutProgress, useSubjects } from '../../shared/api/hooks'

const STATUS = [
  ['not_started', 'Não iniciado'],
  ['in_progress', 'Em andamento'],
  ['first_pass', 'Primeira passagem'],
  ['reviewed', 'Revisado'],
] as const

const PAPER_COLOR = { P1: 'text-p1', P2: 'text-p2', P3: 'text-p3' } as const

export function CatalogPage() {
  const { data } = useSubjects()
  const put = usePutProgress()
  if (!data) return <p className="text-muted" aria-busy="true">Carregando…</p>
  return (
    <div className="space-y-4">
      <h1 className="font-display text-xl font-bold">Edital</h1>
      <p className="text-sm text-muted">Cobertura declarada não mede domínio do conteúdo.</p>
      {data.items.map((s) => (
        <details key={s.id} className="rounded-lg border border-border bg-surface p-3">
          <summary className="cursor-pointer font-semibold">
            <span className={`num mr-2 ${PAPER_COLOR[s.paper]}`}>{s.paper} {s.id}</span>{s.title}
          </summary>
          <ul className="mt-2 space-y-1">
            {s.topics.map((t) => (
              <li key={t.id} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="num text-muted">{t.id}</span>
                <span className="min-w-0 flex-1">{t.title}</span>
                <select aria-label={`Estado de ${t.id}`} value={t.progress?.status ?? 'not_started'}
                  onChange={(e) => put.mutate({ topicId: t.id, status: e.target.value, version: t.progress?.version })}
                  className="rounded-md border border-border bg-surface-2 px-2 py-1">
                  {STATUS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </li>
            ))}
          </ul>
        </details>
      ))}
    </div>
  )
}
```

`apps/web/src/features/settings/SettingsPage.tsx`:

```tsx
import { useState, type FormEvent } from 'react'

import { useDayOffs, useDeleteDayOff, usePutDayOff } from '../../shared/api/hooks'
import { formatDay } from '../../shared/format'

export function SettingsPage() {
  const { data } = useDayOffs()
  const put = usePutDayOff()
  const del = useDeleteDayOff()
  const [day, setDay] = useState('')
  const [reason, setReason] = useState('Feriado')

  function submit(e: FormEvent) {
    e.preventDefault()
    put.mutate({ day, reason })
  }

  return (
    <div className="space-y-4">
      <h1 className="font-display text-xl font-bold">Configurações</h1>
      <section className="rounded-lg border border-border bg-surface p-4">
        <h2 className="font-display font-semibold">Folgas</h2>
        <p className="text-sm text-muted">Dia útil neutro para a sequência: não quebra nem conta.</p>
        <form onSubmit={submit} className="mt-3 flex flex-wrap items-end gap-2">
          <label className="text-sm">Data
            <input type="date" required value={day} onChange={(e) => setDay(e.target.value)}
              className="ml-1 rounded-md border border-border bg-surface-2 px-2 py-1" />
          </label>
          <label className="text-sm">Motivo
            <input required maxLength={100} value={reason} onChange={(e) => setReason(e.target.value)}
              className="ml-1 rounded-md border border-border bg-surface-2 px-2 py-1" />
          </label>
          <button className="rounded-md bg-primary px-3 py-1 text-sm text-white">Marcar folga</button>
        </form>
        {put.error && <p role="alert" className="mt-2 text-sm text-danger">{put.error.message}</p>}
        <ul className="mt-3 space-y-1">
          {data?.items.map((d) => (
            <li key={d.day} className="flex items-center gap-2 text-sm">
              <span className="flex-1">{formatDay(d.day)} · {d.reason}</span>
              <button onClick={() => del.mutate(d.day)} className="text-muted">Remover</button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
```

`apps/web/src/app/App.tsx`, versão final:

```tsx
import { NavLink, Route, Routes } from 'react-router-dom'

import { CatalogPage } from '../features/catalog/CatalogPage'
import { CyclePage } from '../features/cycle/CyclePage'
import { SettingsPage } from '../features/settings/SettingsPage'
import { TodayPage } from '../features/today/TodayPage'
import { Hud } from './Hud'

const LINKS = [
  { to: '/', label: 'Hoje' },
  { to: '/ciclo', label: 'Ciclo' },
  { to: '/edital', label: 'Edital' },
  { to: '/config', label: 'Config.' },
]

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 font-display text-sm font-semibold ${isActive ? 'bg-surface-2 text-xp' : 'text-muted hover:text-text'}`

export function App() {
  return (
    <div className="md:flex">
      <nav aria-label="Principal" className="fixed inset-x-0 bottom-0 z-40 flex justify-around border-t border-border bg-surface
        md:static md:h-screen md:w-48 md:flex-col md:justify-start md:gap-1 md:border-r md:border-t-0 md:p-4">
        <p className="hidden pb-4 font-display text-lg font-bold text-xp md:block">CGU 2026</p>
        {LINKS.map((l) => <NavLink key={l.to} to={l.to} end className={linkClass}>{l.label}</NavLink>)}
      </nav>
      <div className="min-h-screen flex-1 pb-20 md:pb-0">
        <Hud />
        <main className="mx-auto max-w-3xl p-4">
          <Routes>
            <Route path="/" element={<TodayPage />} />
            <Route path="/ciclo" element={<CyclePage />} />
            <Route path="/edital" element={<CatalogPage />} />
            <Route path="/config" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: PWA**

`apps/web/public/manifest.webmanifest`:

```json
{
  "name": "CGU 2026 — Rotina de estudos",
  "short_name": "CGU 2026",
  "lang": "pt-BR",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0B1220",
  "theme_color": "#0B1220",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable" }
  ]
}
```

`scripts/make_icons.py`:

```python
"""Gera os ícones PNG do PWA (192 e 512 px) sem dependências externas.

Uso: python3 scripts/make_icons.py apps/web/public/icons
"""

import struct
import sys
import zlib
from pathlib import Path

BG = (0x0B, 0x12, 0x20)
XP = (0xFA, 0xCC, 0x15)
BLUE = (0x3B, 0x82, 0xF6)


def pixel(x: int, y: int, size: int) -> tuple[int, int, int]:
    u, v = x / size, y / size
    if 0.22 <= u <= 0.60 and 0.62 <= v <= 0.72:
        return XP  # parte preenchida da barra de XP
    if 0.22 <= u <= 0.78 and 0.62 <= v <= 0.72:
        return BLUE
    cx, cy, r = 0.5, 0.40, 0.18
    if (u - cx) ** 2 + (v - cy) ** 2 <= r * r and not ((u - cx) ** 2 + (v - cy) ** 2 <= (r * 0.55) ** 2):
        return XP  # anel da missão
    return BG


def png(size: int) -> bytes:
    rows = b"".join(
        b"\x00" + bytes(c for x in range(size) for c in pixel(x, y, size)) for y in range(size)
    )

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        (out / f"icon-{size}.png").write_bytes(png(size))
        print(f"{out}/icon-{size}.png")


if __name__ == "__main__":
    main()
```

```bash
python3 scripts/make_icons.py apps/web/public/icons
```

Expected: `icon-192.png` e `icon-512.png`; anel amarelo e barra amarela/azul sobre fundo `#0B1220`.

- [ ] **Step 3: Testes e build**

Run: `cd apps/web && npm test && npm run build`
Expected: `Tests 4 passed`; `✓ built`.

- [ ] **Step 4: Commit**

```bash
git add apps/web scripts/make_icons.py
git commit -m "feat(web): ciclo, edital, folgas e PWA instalável"
```

---

### Task 13: Subir a v1, backup e verificação de uso (F1.6)

**Files:**
- Create: `ops/backup.sh`, `scripts/restore-check.sh`
- Modify: `README.md` (seção “Como rodar”)

**Interfaces:**
- Consumes: todas as tarefas anteriores.
- Produces: stack `app + db + backup` em `127.0.0.1:8080`; tag `v1`.

- [ ] **Step 1: Scripts de backup e restauração**

`ops/backup.sh`:

```bash
#!/bin/sh
# Backup diário do banco: um dump ao iniciar e depois a cada 24 h; mantém 14 arquivos.
set -eu
while true; do
  file="/backups/cgu-$(date +%Y%m%d-%H%M%S).dump"
  if pg_dump -Fc -f "$file.tmp"; then
    mv "$file.tmp" "$file"
    echo "backup ok: $file"
  else
    rm -f "$file.tmp"
    echo "backup FALHOU" >&2
  fi
  ls -1t /backups/cgu-*.dump 2>/dev/null | tail -n +15 | xargs -r rm -f
  sleep 86400
done
```

`scripts/restore-check.sh`:

```bash
#!/bin/sh
# Restaura um dump numa database temporária e mostra contagens, sem tocar no banco principal.
# Uso: scripts/restore-check.sh backups/cgu-AAAAMMDD-HHMMSS.dump
set -eu
file="$1"
target="cgu_restore_check"
docker compose exec -T db dropdb -U cgu --if-exists "$target"
docker compose exec -T db createdb -U cgu "$target"
docker compose exec -T db pg_restore -U cgu -d "$target" --no-owner < "$file"
docker compose exec -T db psql -U cgu -d "$target" -c \
  "select (select count(*) from topics) topicos, (select count(*) from occurrences) ocorrencias,
          (select count(*) from study_sessions) sessoes, (select count(*) from daily_missions) missoes;"
docker compose exec -T db dropdb -U cgu "$target"
```

```bash
chmod +x scripts/restore-check.sh
```

- [ ] **Step 2: Subir a stack de produção local**

```bash
docker compose up -d --build
curl -s http://127.0.0.1:8080/api/v1/health
curl -s -o /dev/null -w "%{http_code}\n" -H "Host: evil.example" http://127.0.0.1:8080/api/v1/health
ls backups/
```

Expected: `{"status":"ok"}`; `400`; um arquivo `cgu-AAAAMMDD-HHMMSS.dump`.

- [ ] **Step 3: Jornada real de 09/10 pela interface**

Abrir `http://127.0.0.1:8080`, clicar **Abrir o dia** (gera a semana parcial: S13, S14, S15), registrar a sessão do bloco “Antes” e confirmar o toast `+XP`, o anel 1/3 e o HUD. Depois:

```bash
docker compose restart app && sleep 5
curl -s http://127.0.0.1:8080/api/v1/game/summary
```

Expected: `xp_total` igual ao exibido antes do reinício; `streak.current` = 1 se a sessão tiver ≥ 30 min.

- [ ] **Step 4: Ensaio de restauração**

```bash
docker compose exec -T backup sh -c 'pg_dump -Fc -f /backups/manual.dump'
scripts/restore-check.sh backups/manual.dump
```

Expected: tabela com `topicos = 68`, `ocorrencias = 3` e as contagens reais de sessões e missões.

- [ ] **Step 5: Acesso pelo celular (Tailscale)**

O Tailscale não estava instalado no Mac em 09/10/2026. Instalar o app do Tailscale no Mac e no celular, entrar na mesma conta e então:

```bash
tailscale serve --bg 8080
tailscale serve status        # mostra https://<mac>.<tailnet>.ts.net
```

Acrescentar o nome mostrado em `ALLOWED_HOSTS` no `.env` (ex.: `127.0.0.1,localhost,mac.tail1234.ts.net`), rodar `docker compose up -d app`, abrir o endereço no celular, **Adicionar à tela de início**, registrar uma sessão e conferir no Mac.

- [ ] **Step 6: Acessibilidade e responsividade**

Conferir em 360 px (DevTools) e no desktop: navegação inteira por teclado com foco visível, texto a 200% sem corte, e o macOS com “Reduzir movimento” desligando as animações da barra e do anel.

- [ ] **Step 7: README e tag**

Atualizar “Como rodar” no `README.md`: `cp .env.example .env`, `docker compose up -d --build`, `docker compose --profile test run --rm test`, `cd apps/web && npm test`, `scripts/restore-check.sh`, `tailscale serve --bg 8080` e a observação de que o Mac precisa estar ligado.

```bash
git add ops scripts README.md
git commit -m "chore: backup diário, ensaio de restauração e instruções de uso da v1"
git tag v1
```

---

## Depois da v1

Usar por 2 dias e anotar atritos. Em seguida, escrever o plano da F2 (questões, erros, metas semanais), que vai: passar `settings.daily_question_goal` para `build_mission`, preencher `DayFacts.question_items` e acrescentar as fontes de XP de questões e erros ao `xp_ledger`.
