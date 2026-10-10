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
