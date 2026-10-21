"""Entrada e saída do gerador de flashcards (R16): só o que cabe nos subitens do edital do tópico."""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CATEGORIES = ("conceito", "distincao", "condicao", "causa_consequencia", "aplicacao", "erro_recorrente", "fundamentacao")
MAX_CARDS = 10
MAX_PRIORITIES = 3


@dataclass(frozen=True)
class Context:
    subject: str
    topic_id: str
    topic: str
    subitems: list[str]
    materials: list[dict]
    studied: str


@dataclass(frozen=True)
class Card:
    category: str
    subitem: str
    front: str
    back: str


@dataclass(frozen=True)
class Batch:
    origin: str
    focus: str
    priorities: list[str]
    cards: list[Card]


OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["origem", "foco", "prioridades", "cards"],
    "properties": {
        "origem": {"type": "string"},
        "foco": {"type": "string"},
        "prioridades": {"type": "array", "items": {"type": "string"}},
        "cards": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["categoria", "subitem", "frente", "verso"],
                "properties": {
                    "categoria": {"type": "string", "enum": list(CATEGORIES)},
                    "subitem": {"type": "string"},
                    "frente": {"type": "string"},
                    "verso": {"type": "string"},
                },
            },
        },
    },
}

_CODE = re.compile(r"\d+(?:\.\d+)*")


def subitem_code(text: str) -> str:
    match = _CODE.search(text)
    return match.group(0) if match else ""


def user_input(ctx: Context) -> str:
    parts = [
        f"Disciplina: {ctx.subject}",
        f"Tópico: {ctx.topic_id} {ctx.topic}",
        "Subitens do edital (use apenas estes):\n" + "\n".join(f"- {s}" for s in ctx.subitems),
    ]
    if ctx.materials:
        parts.append("Materiais sugeridos (não acessíveis; só título e nota):\n"
                     + "\n".join(f"- {m['titulo']}: {m.get('nota', '')}" for m in ctx.materials))
    studied = ctx.studied.strip() or "Não informado — use apenas os subitens e indique origem 'tópico informado'."
    parts.append(f"O que estudei / errei:\n{studied}")
    return "\n\n".join(parts)


def parse_batch(raw: dict, ctx: Context) -> Batch:
    allowed = {subitem_code(s) for s in ctx.subitems}
    cards = []
    for c in raw.get("cards", []):
        code = subitem_code(c.get("subitem", ""))
        front, back = c.get("frente", "").strip(), c.get("verso", "").strip()
        if code in allowed and front and back and c.get("categoria") in CATEGORIES:
            cards.append(Card(c["categoria"], code, front, back))
    return Batch(raw.get("origem", "").strip(), raw.get("foco", "").strip(),
                 [p.strip() for p in raw.get("prioridades", []) if p.strip()][:MAX_PRIORITIES], cards[:MAX_CARDS])


@lru_cache
def load_prompt() -> str:
    return (Path(__file__).parent / "prompt.md").read_text(encoding="utf-8")
