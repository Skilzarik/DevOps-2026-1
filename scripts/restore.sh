#!/usr/bin/env bash
# Восстановление БД из резервной копии (make restore FILE=backups/xxx.dump).
# Текущее содержимое базы ЗАМЕНЯЕТСЯ. Без ASSUME_YES=1 спрашивает подтверждение.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PY:-$ROOT/backend/venv/bin/python}"
FILE="${1:?Использование: restore.sh <файл.dump>}"

[ -f "$FILE" ] || { echo "Файл не найден: $FILE" >&2; exit 1; }
command -v pg_restore >/dev/null || { echo "pg_restore не найден (пакет postgresql-client)" >&2; exit 1; }
eval "$("$PY" "$ROOT/scripts/pgenv.py" "${DB_URL_VAR:-DATABASE_URL}")"

pg_restore --list "$FILE" >/dev/null   # проверка, что это корректный архив pg_dump

if [ "${ASSUME_YES:-0}" != 1 ]; then
  read -r -p "Заменить данные базы '$PGDATABASE' ($PGHOST) копией $FILE? [y/N] " answer
  [ "$answer" = y ] || { echo "Отменено"; exit 1; }
fi

# Одна транзакция: при ошибке база остаётся в прежнем состоянии.
pg_restore --clean --if-exists --no-owner --single-transaction --exit-on-error \
  --dbname="$PGDATABASE" "$FILE"
echo "Восстановлено из $FILE"
