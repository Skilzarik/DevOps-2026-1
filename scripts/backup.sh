#!/usr/bin/env bash
# Резервная копия БД в формате pg_dump custom (make backup).
# Подключение берётся из DATABASE_URL (окружение или backend/.env); пароль не попадает в argv.
# Переменные: BACKUP_DIR (по умолчанию ./backups), DB_URL_VAR (по умолчанию DATABASE_URL).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PY:-$ROOT/backend/venv/bin/python}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"

command -v pg_dump >/dev/null || { echo "pg_dump не найден (пакет postgresql-client)" >&2; exit 1; }
eval "$("$PY" "$ROOT/scripts/pgenv.py" "${DB_URL_VAR:-DATABASE_URL}")"

mkdir -p "$BACKUP_DIR"
OUT="$BACKUP_DIR/${PGDATABASE}_$(date +%Y%m%d_%H%M%S).dump"
umask 077
pg_dump --format=custom --no-owner --file="$OUT"
echo "Резервная копия: $OUT"
