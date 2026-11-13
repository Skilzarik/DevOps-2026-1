#!/usr/bin/env bash
# make up: сборка образа, запуск окружения и ожидание готовности всех сервисов.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/container_lib.sh"
need_docker
[ -f "$ENV_FILE" ] || bash scripts/container_env.sh

compose build
compose up -d

for svc in db app1 app2 nginx; do
  if ! wait_healthy "$svc" 120; then
    echo "Сервис $svc не стал healthy за 120 секунд" >&2
    compose ps
    compose logs --tail 30 "$svc" >&2 || true
    exit 1
  fi
done

compose ps
echo
echo "Готово: http://<адрес этой машины>:$(env_value HTTP_PORT)/"
