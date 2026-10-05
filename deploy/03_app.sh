#!/usr/bin/env bash
# 03_app.sh - сервер приложения: код, venv, настройки, systemd-служба.
# Запуск на app от root (после 01_base.sh ROLE=app и 02_db.sh):
#   sudo bash deploy/03_app.sh
# Пароли запрашиваются без отображения или берутся из окружения (sudo -E):
#   APP_DB_PASSWORD      - пароль appuser (нужен, если /etc/myapp/myapp.env ещё нет)
#   MIGRATOR_DB_PASSWORD - пароль migrator (нужен для первого создания таблиц; пропуск: SKIP_INIT_TABLES=1)
# Скрипт можно запускать повторно: код обновляется, настройки и SECRET_KEY сохраняются.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_URL="${REPO_URL:-https://github.com/Skilzarik/DevOps-2026-1.git}"
BRANCH="${BRANCH:-main}"
APP_DIR="${APP_DIR:-/opt/myapp}"
VENV="$APP_DIR/venv"
ENV_DIR=/etc/myapp
ENV_FILE="$ENV_DIR/myapp.env"
DB_HOST="${DB_HOST:-192.168.56.20}"
DB_NAME="${DB_NAME:-music_store}"
APP_DB_USER="${APP_DB_USER:-appuser}"
MIGRATOR_USER="${MIGRATOR_USER:-migrator}"
APP_PORT="${APP_PORT:-8000}"

[ "$(id -u)" -eq 0 ] || { echo "Запустите через sudo" >&2; exit 1; }
id appsvc >/dev/null 2>&1 || { echo "Нет пользователя appsvc: сначала 01_base.sh с ROLE=app" >&2; exit 1; }
[ -f "$SCRIPT_DIR/myapp.service" ] || { echo "Рядом со скриптом нет myapp.service" >&2; exit 1; }

ask_secret() {   # ask_secret ИМЯ_ПЕРЕМЕННОЙ "Приглашение"
  local n="$1"
  if [ -z "${!n:-}" ]; then
    [ -t 0 ] || { echo "Задайте $n в окружении (sudo -E) или запустите интерактивно" >&2; exit 1; }
    read -r -s -p "$2: " "$n"; echo
  fi
  [[ "${!n}" =~ ^[A-Za-z0-9]+$ ]] || { echo "$n: допустимы только латинские буквы и цифры" >&2; exit 1; }
  export "$n"
}

echo "== [1/7] Пакеты"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv git libpq5 curl openssl postgresql-client netcat-openbsd

echo "== [2/7] Проверка доступности БД ($DB_HOST:5432)"
timeout 5 bash -c "</dev/tcp/$DB_HOST/5432" 2>/dev/null \
  || { echo "БД недоступна с этого сервера. Проверьте 02_db.sh, адреса и файрвол на db." >&2; exit 1; }

echo "== [3/7] Код приложения"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch --quiet origin "$BRANCH"
  git -C "$APP_DIR" checkout --quiet "$BRANCH"
  git -C "$APP_DIR" pull --ff-only --quiet origin "$BRANCH"
else
  if [ -d "$APP_DIR" ] && [ -n "$(ls -A "$APP_DIR")" ]; then
    echo "$APP_DIR не пуст и это не git-репозиторий. Очистите: find $APP_DIR -mindepth 1 -delete" >&2
    exit 1
  fi
  git clone --quiet --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

echo "== [4/7] Виртуальное окружение и зависимости"
REQ="$APP_DIR/backend/requirements.txt"
[ -f "$REQ" ] || { echo "Нет $REQ: добавьте requirements.txt в репозиторий" >&2; exit 1; }
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$REQ"
"$VENV/bin/python" -c 'import psycopg' 2>/dev/null || "$VENV/bin/pip" install -q "psycopg[binary]"

echo "== [5/7] Настройки отдельно от кода ($ENV_FILE)"
install -d -o root -g appsvc -m 750 "$ENV_DIR"
if [ ! -f "$ENV_FILE" ] || [ "${FORCE_ENV:-0}" = 1 ]; then
  ask_secret APP_DB_PASSWORD "Пароль $APP_DB_USER"
  umask 077
  cat > "$ENV_FILE" <<ENV
DATABASE_URL=postgresql+psycopg://$APP_DB_USER:$APP_DB_PASSWORD@$DB_HOST:5432/$DB_NAME
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
APP_PORT=$APP_PORT
ENV
  chown root:appsvc "$ENV_FILE"
  chmod 640 "$ENV_FILE"
else
  echo "файл уже есть, оставляю без изменений (FORCE_ENV=1 - пересоздать)"
fi

echo "== [6/7] Таблицы БД (под ролью $MIGRATOR_USER; у $APP_DB_USER прав на DDL нет)"
if [ "${SKIP_INIT_TABLES:-0}" = 1 ]; then
  echo "пропущено (SKIP_INIT_TABLES=1)"
else
  ask_secret MIGRATOR_DB_PASSWORD "Пароль $MIGRATOR_USER"
  ( cd "$APP_DIR/backend" && \
    DATABASE_URL="postgresql+psycopg://$MIGRATOR_USER:$MIGRATOR_DB_PASSWORD@$DB_HOST:5432/$DB_NAME" \
    SECRET_KEY=tmp "$VENV/bin/python" -c \
    "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)" )
fi

echo "== Права: код принадлежит root, приложение только читает"
chown -R root:appsvc "$APP_DIR"
chmod -R u=rwX,g=rX,o= "$APP_DIR"

echo "== [7/7] systemd-служба"
install -m 644 "$SCRIPT_DIR/myapp.service" /etc/systemd/system/myapp.service
systemctl daemon-reload
systemctl enable myapp
systemctl restart myapp

PORT="$(grep -E '^APP_PORT=' "$ENV_FILE" | cut -d= -f2 || true)"; PORT="${PORT:-8000}"
ok=0
for _ in $(seq 1 20); do
  if out="$(curl -fsS "http://127.0.0.1:$PORT/health" 2>/dev/null)"; then echo "health: $out"; ok=1; break; fi
  sleep 1
done
systemctl --no-pager status myapp | head -n 8 || true
if [ "$ok" != 1 ]; then
  echo "Приложение не ответило на /health. Журнал: journalctl -u myapp -n 50 --no-pager" >&2
  exit 1
fi
echo "Готово: 03_app.sh"
