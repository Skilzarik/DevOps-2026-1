#!/usr/bin/env bash
# Общие функции контейнерных скриптов (подключается командой source).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ENV_FILE="${ENV_FILE:-.env.docker}"

# Все команды docker compose выполняются с файлом настроек .env.docker.
# Имя проекта можно переопределить переменной COMPOSE_PROJECT_NAME (так создаётся второе окружение).
compose() { docker compose --env-file "$ENV_FILE" "$@"; }

need_docker() {
  command -v docker >/dev/null 2>&1 || { echo "Docker не установлен" >&2; exit 1; }
  docker info >/dev/null 2>&1 || {
    echo "Нет доступа к Docker. Проверьте, что служба запущена и пользователь в группе docker" >&2
    exit 1
  }
  docker compose version >/dev/null 2>&1 || { echo "Нет плагина docker compose" >&2; exit 1; }
}

need_env() {
  [ -f "$ENV_FILE" ] || { echo "Нет $ENV_FILE. Выполните: make container-env" >&2; exit 1; }
}

env_value() { grep -E "^$1=" "$ENV_FILE" | head -n1 | cut -d= -f2-; }

# wait_healthy СЕРВИС [СЕКУНД]: ждёт статуса healthy
wait_healthy() {
  local svc="$1" timeout="${2:-120}" cid status
  for _ in $(seq 1 "$timeout"); do
    cid="$(compose ps -q "$svc" 2>/dev/null | head -n1)"
    if [ -n "$cid" ]; then
      status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null || echo none)"
      [ "$status" = healthy ] && return 0
    fi
    sleep 1
  done
  return 1
}

# Выполняет SQL внутри контейнера БД от имени суперпользователя (локальный сокет, пароль не нужен)
db_sql() { compose exec -T db psql -U postgres -d music_store -tA -v ON_ERROR_STOP=1 "$@"; }

db_counts() {
  db_sql -c "select 'users='||(select count(*) from users)||' musicians='||(select count(*) from musicians)||' discs='||(select count(*) from discs)||' sales='||(select count(*) from sales)"
}
