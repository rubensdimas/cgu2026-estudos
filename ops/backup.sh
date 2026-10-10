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
