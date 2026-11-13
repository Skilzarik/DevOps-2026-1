#!/usr/bin/env bash
# make container-check: автоматическая проверка контейнерного окружения.
# Окружение не принимается, если нарушено любое эксплуатационное требование.
# Запускается на Linux-машине с Docker (по заданию: на виртуальной машине).
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/container_lib.sh"
need_docker
[ -f "$ENV_FILE" ] || bash scripts/container_env.sh

FAILS=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

ok()   { echo "  [ok]  $*"; }
bad()  { echo "  [FAIL] $*"; FAILS=$((FAILS + 1)); }
step() { echo; echo "== $*"; }
check() { local desc="$1"; shift; if "$@" >/dev/null 2>&1; then ok "$desc"; else bad "$desc"; fi; }

PORT="$(env_value HTTP_PORT)"; PORT="${PORT:-80}"
URL="http://127.0.0.1:$PORT"
VERSION="$(env_value APP_VERSION)"
IMAGE="music-store:$VERSION"

instance_ids() {  # instance_ids N: идентификаторы экземпляров из заголовков N ответов
  local n="$1" i
  for i in $(seq 1 "$n"); do
    curl -s -D - -o /dev/null --max-time 15 "$URL/health" | tr -d '\r' \
      | awk -F': ' 'tolower($1)=="x-instance-id" {print $2}'
  done
}

step "1. Правила: Dockerfile, .dockerignore, compose.yaml (latest, root, секреты, healthcheck, порты)"
if compose config --format json > "$TMP/config.json" 2> "$TMP/config.err"; then
  ok "compose.yaml корректен, все обязательные переменные заданы"
  python3 scripts/check_container_policy.py --config "$TMP/config.json" && ok "правила соблюдены" || bad "нарушены контейнерные правила"
else
  bad "compose config не выполнился: $(head -n3 "$TMP/config.err")"
fi

step "2. Сборка образа"
if compose build > "$TMP/build.log" 2>&1; then
  ok "образ $IMAGE собран"
else
  bad "сборка не удалась"; tail -n 20 "$TMP/build.log"; echo "Дальнейшие проверки невозможны"; exit 1
fi
user="$(docker image inspect -f '{{.Config.User}}' "$IMAGE")"
case "$user" in ""|0|root|root:*|0:*) bad "в образе нет непривилегированного пользователя (USER='$user')" ;; *) ok "образ запускается от пользователя $user" ;; esac
if docker image inspect -f '{{json .Config.Env}}' "$IMAGE" | grep -qiE 'PASSWORD|SECRET'; then
  bad "в переменных окружения образа есть секреты"
else
  ok "в переменных окружения образа нет секретов"
fi
check "в образе нет файлов .env" docker run --rm --entrypoint sh "$IMAGE" -c 'test ! -e /app/.env && test ! -e /app/backend/.env'
check "в образе задан HEALTHCHECK" sh -c "docker image inspect -f '{{json .Config.Healthcheck}}' '$IMAGE' | grep -q Test"
norm() { grep -v '^#' | grep -v '^$' | tr 'A-Z_' 'a-z-' | sort; }
docker run --rm --entrypoint python "$IMAGE" -m pip freeze 2>/dev/null | norm > "$TMP/image.txt"
norm < backend/requirements.txt > "$TMP/lock.txt"
if diff -q "$TMP/lock.txt" "$TMP/image.txt" >/dev/null; then
  ok "версии зависимостей в образе совпадают с backend/requirements.txt (сборка воспроизводима)"
else
  bad "зависимости образа отличаются от requirements.txt"; diff "$TMP/lock.txt" "$TMP/image.txt" | head -n 10
fi

step "3. Запуск окружения: порядок, healthcheck, миграции"
if compose up -d > "$TMP/up.log" 2>&1; then ok "окружение запущено"; else bad "запуск не удался"; tail -n 15 "$TMP/up.log"; fi
for svc in db app1 app2 nginx; do
  if wait_healthy "$svc" 120; then ok "$svc: healthy"; else bad "$svc: не стал healthy"; compose logs --tail 15 "$svc"; fi
done
mig="$(docker inspect -f '{{.State.ExitCode}}' "$(compose ps -aq migrate | head -n1)" 2>/dev/null || echo '?')"
[ "$mig" = 0 ] && ok "миграции выполнены (migrate завершился с кодом 0)" || bad "миграции: код завершения $mig"

step "4. Пользователь процессов (не root)"
for svc in db app1 app2 nginx; do
  uid="$(compose exec -T "$svc" stat -c %u /proc/1 2>/dev/null | tr -d '\r')"
  if [ -n "$uid" ] && [ "$uid" != 0 ]; then ok "$svc: главный процесс работает от uid $uid"; else bad "$svc: главный процесс от root или не определён (uid='$uid')"; fi
done

step "5. Порты: БД и приложение наружу не публикуются"
[ -z "$(compose port db 5432 2>/dev/null)" ] && ok "порт БД не опубликован" || bad "порт БД опубликован"
[ -z "$(compose port app1 8000 2>/dev/null)" ] && [ -z "$(compose port app2 8000 2>/dev/null)" ] \
  && ok "приложение недоступно напрямую (порты не опубликованы)" || bad "порт приложения опубликован"
[ -n "$(compose port nginx 8080 2>/dev/null)" ] && ok "наружу опубликован только nginx" || bad "nginx не публикует порт"

step "6. Доступ через nginx и распределение запросов"
code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$URL/health")"
[ "$code" = 200 ] && ok "GET /health через nginx: 200" || bad "GET /health через nginx: $code"
ctype="$(curl -s -o /dev/null -w '%{content_type}' --max-time 15 "$URL/")"
case "$ctype" in text/html*) ok "главная страница отдаётся" ;; *) bad "главная страница: $ctype" ;; esac
ids="$(instance_ids 20 | sort -u)"
count="$(printf '%s\n' "$ids" | grep -c .)"
[ "$count" -ge 2 ] && ok "ответили разные экземпляры: $(echo $ids)" || bad "ответил один экземпляр: '$ids' (ожидалось не менее двух)"

step "7. Корректная остановка и отказоустойчивость"
cid="$(compose ps -q app1 | head -n1)"
t0="$(date +%s)"
compose stop app1 >/dev/null 2>&1
t1="$(date +%s)"
exit_code="$(docker inspect -f '{{.State.ExitCode}}' "$cid")"
[ $((t1 - t0)) -lt 15 ] && ok "контейнер остановился за $((t1 - t0)) с (без принудительного kill)" || bad "остановка заняла $((t1 - t0)) с"
case "$exit_code" in 0|143) ok "код завершения $exit_code (штатная остановка по SIGTERM)" ;; *) bad "код завершения $exit_code (137 означает принудительный kill)" ;; esac
docker logs "$cid" 2>&1 | grep -q "shutdown complete" && ok "в журнале есть корректное завершение приложения" || bad "в журнале нет записи о завершении"
fails=0; for i in $(seq 1 15); do c="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$URL/health")"; [ "$c" = 200 ] || fails=$((fails + 1)); done
[ "$fails" = 0 ] && ok "при остановленном app1 сервис доступен (15 из 15 запросов успешны)" || bad "при остановленном app1 неуспешных запросов: $fails из 15"
only="$(instance_ids 6 | sort -u | tr '\n' ' ')"
[ "$only" = "app2 " ] && ok "отвечает только app2" || bad "ответили: '$only'"
compose start app1 >/dev/null 2>&1
wait_healthy app1 60 && ok "app1 снова healthy" || bad "app1 не вернулся"

step "8. Ограничение частоты запросов"
sleep 3
codes="$(seq 1 80 | xargs -P 40 -I{} curl -s -o /dev/null -w '%{http_code}\n' --max-time 15 "$URL/health" | sort | uniq -c)"
echo "$codes" | grep -q ' 429$' && echo "$codes" | grep -q ' 200$' && ok "при превышении лимита nginx отвечает 429" || { bad "ограничение частоты не сработало"; echo "$codes"; }
sleep 4

step "9. Сохранность данных: пересоздание контейнеров и обновление образа"
db_sql -c "DELETE FROM users WHERE username='persist_probe'" >/dev/null 2>&1
db_sql -c "INSERT INTO users (username, hashed_password, role) VALUES ('persist_probe', 'x', 'seller')" >/dev/null 2>&1 \
  && ok "в БД добавлена контрольная запись" || bad "не удалось добавить контрольную запись"
probe() { db_sql -c "SELECT count(*) FROM users WHERE username='persist_probe'" 2>/dev/null | tr -d '\r\n'; }
compose down > "$TMP/down.log" 2>&1
compose up -d > "$TMP/up2.log" 2>&1
for svc in db app1 app2 nginx; do wait_healthy "$svc" 120 || bad "$svc не поднялся после пересоздания"; done
[ "$(probe)" = 1 ] && ok "после down/up данные на месте (volume сохранён)" || bad "данные потеряны после пересоздания контейнеров"
docker tag "$IMAGE" "$IMAGE-upd"
APP_VERSION="$VERSION-upd" compose up -d > "$TMP/up3.log" 2>&1
for svc in app1 app2 nginx; do wait_healthy "$svc" 120 || bad "$svc не поднялся после обновления образа"; done
img="$(docker inspect -f '{{.Config.Image}}' "$(compose ps -q app1 | head -n1)")"
[ "$img" = "$IMAGE-upd" ] && ok "контейнеры пересозданы из обновлённого образа" || bad "образ не обновился (используется $img)"
[ "$(probe)" = 1 ] && ok "после обновления образа данные на месте" || bad "данные потеряны после обновления образа"
compose up -d > "$TMP/up4.log" 2>&1
for svc in app1 app2 nginx; do wait_healthy "$svc" 120; done
docker rmi "$IMAGE-upd" >/dev/null 2>&1 || true

step "10. Резервная копия и восстановление в новый volume"
before="$(db_counts | tr -d '\r\n')"
backup_out="$(bash scripts/container_backup.sh 2>&1)"; backup_file="$(printf '%s\n' "$backup_out" | sed -n 's/^Резервная копия: //p')"
[ -n "$backup_file" ] && [ -s "$backup_file" ] && ok "резервная копия создана: $backup_file" || { bad "резервная копия не создана: $backup_out"; }
if [ -n "$backup_file" ] && [ -s "$backup_file" ]; then
  if ASSUME_YES=1 bash scripts/container_restore.sh --new-volume "$backup_file" > "$TMP/restore.log" 2>&1; then
    after="$(COMPOSE_PROJECT_NAME=music-restore db_counts | tr -d '\r\n')"
    [ "$before" = "$after" ] && ok "в новом volume те же данные: $after" || bad "данные различаются: было '$before', стало '$after'"
  else
    bad "восстановление в новый volume не удалось"; tail -n 15 "$TMP/restore.log"
  fi
  COMPOSE_PROJECT_NAME=music-restore compose down -v >/dev/null 2>&1
  docker volume ls -q | grep -q '^music-restore_pgdata$' && bad "временный volume не удалён" || ok "временное окружение удалено вместе с volume"
fi
db_sql -c "DELETE FROM users WHERE username='persist_probe'" >/dev/null 2>&1

step "11. Ограничения ресурсов применены к контейнерам"
for svc in db app1 app2 nginx; do
  cid="$(compose ps -q "$svc" | head -n1)"
  mem="$(docker inspect -f '{{.HostConfig.Memory}}' "$cid")"; cpu="$(docker inspect -f '{{.HostConfig.NanoCpus}}' "$cid")"
  if [ "${mem:-0}" -gt 0 ] && [ "${cpu:-0}" -gt 0 ]; then ok "$svc: память $((mem / 1048576)) МБ, процессор $(awk "BEGIN{print $cpu/1000000000}")"; else bad "$svc: лимиты не применены"; fi
done

echo
if [ "$FAILS" -eq 0 ]; then
  echo "container-check: ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ"
  echo "Окружение оставлено запущенным (остановить: make down)"
  exit 0
fi
echo "container-check: НЕ ПРОЙДЕНО проверок: $FAILS"
exit 1
