#!/usr/bin/env bash
# Фиксирует точные версии всех зависимостей (make lock).
# Читает backend/requirements.in и requirements-dev.in, пишет requirements.txt и requirements-dev.txt.
# Версия Python должна совпадать с серверной (Debian 13: 3.13):  PYTHON=python3.13 make lock
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

"$PYTHON" -m venv "$TMP/v"
"$TMP/v/bin/pip" install -q --upgrade pip

"$TMP/v/bin/pip" install -q -r "$ROOT/backend/requirements.in"
{ echo "# Сгенерировано командой make lock. Руками не править."; "$TMP/v/bin/pip" freeze; } \
  > "$ROOT/backend/requirements.txt"

"$TMP/v/bin/pip" install -q -r "$ROOT/backend/requirements-dev.in"
{ echo "# Сгенерировано командой make lock (приложение + инструменты проверки). Руками не править."; \
  "$TMP/v/bin/pip" freeze; } > "$ROOT/backend/requirements-dev.txt"

echo "Версии зафиксированы: backend/requirements.txt, backend/requirements-dev.txt"
