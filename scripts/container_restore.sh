#!/usr/bin/env bash
# Восстановление БД из резервной копии в контейнерной среде.
#   make container-restore FILE=backups/x.dump       - в текущую БД (данные заменяются)
#   make container-restore-new FILE=backups/x.dump   - в НОВЫЙ том: отдельный проект music-restore
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/container_lib.sh"

NEW=0
if [ "${1:-}" = "--new-volume" ]; then NEW=1; shift; fi
FILE="${1:?Использование: container_restore.sh [--new-volume] <файл.dump>}"
[ -f "$FILE" ] || { echo "Файл не найден: $FILE" >&2; exit 1; }
need_docker
need_env

restore_into_db() {
  # --role=migrator: восстановленные объекты принадлежат migrator, как после обычных миграций
  compose exec -T db pg_restore -U postgres -d music_store \
    --clean --if-exists --no-owner --role=migrator --single-transaction --exit-on-error < "$FILE"
}

if [ "$NEW" = 1 ]; then
  export COMPOSE_PROJECT_NAME="${RESTORE_PROJECT:-music-restore}"
  echo "Новое окружение '$COMPOSE_PROJECT_NAME' с пустым томом БД"
  compose up -d db
  wait_healthy db 90 || { echo "БД не запустилась" >&2; exit 1; }
  restore_into_db
  echo "После восстановления: $(db_counts)"
  echo "Проверьте приложение на другом порту:"
  echo "  HTTP_PORT=8081 COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME docker compose --env-file $ENV_FILE up -d"
  echo "Удалить это окружение вместе с томом: COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME docker compose --env-file $ENV_FILE down -v"
else
  if [ "${ASSUME_YES:-0}" != 1 ]; then
    read -r -p "Заменить данные текущей БД копией $FILE? [y/N] " answer
    [ "$answer" = y ] || { echo "Отменено"; exit 1; }
  fi
  # Приложение и nginx останавливаются, чтобы никто не писал в БД во время восстановления
  compose stop nginx app1 app2
  restore_into_db
  compose start app1 app2 nginx
  for svc in app1 app2 nginx; do wait_healthy "$svc" 90 || echo "Сервис $svc не стал healthy" >&2; done
  echo "После восстановления: $(db_counts)"
fi
echo "Восстановлено из $FILE"
