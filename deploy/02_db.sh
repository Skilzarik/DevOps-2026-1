#!/usr/bin/env bash
# 02_db.sh - сервер БД: PostgreSQL, роли, база, минимальные права.
# Запуск на db от root:  sudo bash deploy/02_db.sh
# Пароли ролей берутся из окружения (APP_DB_PASSWORD, MIGRATOR_DB_PASSWORD).
# Если роли ещё нет и пароль не задан, он генерируется и один раз выводится на экран.
# Если роль уже есть и пароль не задан, пароль не меняется (повторный запуск безопасен).
# Пароли: только латинские буквы и цифры (они попадают в строку подключения).
set -euo pipefail
cd /tmp

APP_IP="${APP_IP:-192.168.56.10}"
DB_IP="${DB_IP:-192.168.56.20}"
DB_NAME="${DB_NAME:-music_store}"
APP_DB_USER="${APP_DB_USER:-appuser}"
MIGRATOR_USER="${MIGRATOR_USER:-migrator}"
APP_DB_PASSWORD="${APP_DB_PASSWORD:-}"
MIGRATOR_DB_PASSWORD="${MIGRATOR_DB_PASSWORD:-}"

[ "$(id -u)" -eq 0 ] || { echo "Запустите через sudo" >&2; exit 1; }

echo "== [1/5] Установка PostgreSQL"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql openssl
PGVER="$(ls /etc/postgresql | sort -V | tail -n1)"
PGCONF="/etc/postgresql/$PGVER/main"

echo "== [2/5] Сетевые настройки: слушаем только localhost и $DB_IP"
install -d "$PGCONF/conf.d"
cat > "$PGCONF/conf.d/10-lab.conf" <<CONF
listen_addresses = 'localhost,$DB_IP'
CONF

echo "== [3/5] pg_hba.conf: доступ только с $APP_IP"
for u in "$APP_DB_USER" "$MIGRATOR_USER"; do
  line="host  $DB_NAME  $u  $APP_IP/32  scram-sha-256"
  grep -qxF "$line" "$PGCONF/pg_hba.conf" || echo "$line" >> "$PGCONF/pg_hba.conf"
done

systemctl restart postgresql
for _ in $(seq 1 20); do pg_isready -q && break; sleep 1; done
pg_isready -q || { echo "PostgreSQL не запустился (проверьте, что у интерфейса есть адрес $DB_IP)" >&2; exit 1; }

echo "== [4/5] Роли, база, права"
pgsql() { runuser -u postgres -- psql -v ON_ERROR_STOP=1 -q "$@"; }
role_exists() { [ "$(pgsql -tA -c "SELECT 1 FROM pg_roles WHERE rolname='$1'")" = 1 ]; }
GENERATED=()
resolve_pw() {   # resolve_pw ИМЯ_ПЕРЕМЕННОЙ РОЛЬ
  local var="$1" role="$2"
  if [ -n "${!var}" ]; then
    [[ "${!var}" =~ ^[A-Za-z0-9]+$ ]] || { echo "$var: допустимы только латинские буквы и цифры" >&2; exit 1; }
    return
  fi
  if role_exists "$role"; then return; fi          # роль есть - пароль не трогаем
  printf -v "$var" '%s' "$(openssl rand -hex 16)"
  GENERATED+=("$role: ${!var}")
}
resolve_pw APP_DB_PASSWORD "$APP_DB_USER"
resolve_pw MIGRATOR_DB_PASSWORD "$MIGRATOR_USER"

{
cat <<SQL
SELECT 'CREATE ROLE $MIGRATOR_USER LOGIN' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname='$MIGRATOR_USER') \gexec
SELECT 'CREATE ROLE $APP_DB_USER LOGIN' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname='$APP_DB_USER') \gexec
SQL
if [ -n "$MIGRATOR_DB_PASSWORD" ]; then echo "ALTER ROLE $MIGRATOR_USER PASSWORD '$MIGRATOR_DB_PASSWORD';"; fi
if [ -n "$APP_DB_PASSWORD" ]; then echo "ALTER ROLE $APP_DB_USER PASSWORD '$APP_DB_PASSWORD';"; fi
cat <<SQL
SELECT 'CREATE DATABASE $DB_NAME OWNER $MIGRATOR_USER' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname='$DB_NAME') \gexec
ALTER DATABASE $DB_NAME OWNER TO $MIGRATOR_USER;
REVOKE ALL ON DATABASE $DB_NAME FROM PUBLIC;
GRANT CONNECT ON DATABASE $DB_NAME TO $APP_DB_USER;
\connect $DB_NAME
GRANT USAGE ON SCHEMA public TO $APP_DB_USER;
ALTER DEFAULT PRIVILEGES FOR ROLE $MIGRATOR_USER IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO $APP_DB_USER;
ALTER DEFAULT PRIVILEGES FOR ROLE $MIGRATOR_USER IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO $APP_DB_USER;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO $APP_DB_USER;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO $APP_DB_USER;
SQL
} | pgsql -f -

echo "== [5/5] Проверка: на каких адресах слушает PostgreSQL"
ss -tlnp | grep 5432 || true

if [ "${#GENERATED[@]}" -gt 0 ]; then
  echo
  echo "!!! Сгенерированные пароли (показаны один раз, сохраните и не кладите в репозиторий):"
  printf '    %s\n' "${GENERATED[@]}"
fi
echo "Готово: 02_db.sh"
