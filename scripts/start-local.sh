#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

if [ "$#" -eq 0 ]; then
  exec docker compose up -d --build
fi

if [ "$#" -ne 1 ] || [ "$1" != "--restore" ]; then
  printf 'Uso: %s [--restore]\n' "$0" >&2
  exit 2
fi

if ! compose_config=$(docker compose config --format json); then
  printf 'Não foi possível ler a configuração do Compose. Confira o arquivo .env.\n' >&2
  exit 1
fi

if ! backup_dir=$(printf '%s' "$compose_config" | python3 -c '
import json, sys
config = json.load(sys.stdin)
volumes = config["services"]["backup"]["volumes"]
print(next(volume["source"] for volume in volumes if volume["target"] == "/backups"))
'); then
  printf 'Não foi possível resolver BACKUP_DIR no .env.\n' >&2
  exit 1
fi

if [ ! -d "$backup_dir" ]; then
  printf 'BACKUP_DIR não existe: %s\n' "$backup_dir" >&2
  exit 1
fi

latest_dump=$(find "$backup_dir" -maxdepth 1 -type f -name 'cgu-*.dump' -print | LC_ALL=C sort | tail -n 1)
if [ -z "$latest_dump" ]; then
  printf 'Nenhum backup cgu-*.dump encontrado em BACKUP_DIR: %s\n' "$backup_dir" >&2
  exit 1
fi

printf 'Restaurando o backup mais recente: %s\n' "$(basename "$latest_dump")"

docker compose up -d --wait db

database_nonempty=$(docker compose exec -T db psql -U cgu -d cgu -tAc \
  "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema'));")
if [ "$database_nonempty" != "f" ]; then
  printf 'O banco cgu já contém tabelas; restauração cancelada para preservar os dados.\n' >&2
  exit 1
fi

docker compose exec -T db pg_restore --no-owner --exit-on-error -U cgu -d cgu < "$latest_dump"
exec docker compose up -d --build
