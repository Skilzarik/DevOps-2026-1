#!/usr/bin/env bash
# make container-backup: резервная копия БД из контейнера в каталог backups/ на хосте.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/container_lib.sh"
need_docker
need_env

dir="${BACKUP_DIR:-$ROOT/backups}"
mkdir -p "$dir"
out="$dir/container_music_store_$(date +%Y%m%d_%H%M%S).dump"

umask 077
# pg_dump выполняется внутри контейнера, поток записывается в файл на хосте
if ! compose exec -T db pg_dump -U postgres -d music_store --format=custom --no-owner > "$out"; then
  rm -f "$out"
  echo "Не удалось создать копию" >&2
  exit 1
fi
[ -s "$out" ] || { rm -f "$out"; echo "Получена пустая копия" >&2; exit 1; }
echo "Резервная копия: $out"
