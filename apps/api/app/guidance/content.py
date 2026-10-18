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
