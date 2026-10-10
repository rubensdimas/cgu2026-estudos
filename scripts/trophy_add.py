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
