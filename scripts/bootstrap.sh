#!/usr/bin/env bash
# Первоначальная настройка проекта (make setup): окружение, зависимости, настройки, базы, миграции.
# Скрипт можно запускать повторно.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
B=backend

echo "[1/5] Виртуальное окружение"
[ -x "$B/venv/bin/python" ] || "$PYTHON" -m venv "$B/venv"

echo "[2/5] Зависимости (точные версии из requirements-dev.txt)"
[ -f "$B/requirements-dev.txt" ] || "$ROOT/scripts/lock.sh"
"$B/venv/bin/pip" install -q --upgrade pip
"$B/venv/bin/pip" install -q -r "$B/requirements-dev.txt"

echo "[3/5] Файлы настроек (в репозиторий не попадают)"
created=0
if [ ! -f "$B/.env" ]; then
  cp .env.example "$B/.env"; echo "  создан $B/.env из .env.example"; created=1
fi
if [ ! -f "$B/.env.test" ]; then
  cp "$B/.env.test.example" "$B/.env.test"; echo "  создан $B/.env.test из .env.test.example"; created=1
fi
if grep -qE 'CHANGE_ME|your_password|change-me' "$B/.env" "$B/.env.test"; then
  echo "Впишите настоящие значения в $B/.env и $B/.env.test (пароль PostgreSQL, SECRET_KEY)"
  echo "и повторите: make setup"
  exit 1
fi
[ "$created" = 0 ] || echo "  проверьте значения в созданных файлах"

echo "[4/5] Базы данных (рабочая и тестовая)"
"$B/venv/bin/python" scripts/create_databases.py

echo "[5/5] Миграции рабочей БД"
( cd "$B" && venv/bin/alembic upgrade head )

echo "Готово. Дальше: make verify"
