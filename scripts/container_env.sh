#!/usr/bin/env bash
# make container-env: создаёт .env.docker со случайными паролями (если файла ещё нет).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env.docker ]; then
  echo ".env.docker уже существует, оставляю без изменений"
  exit 0
fi

cp .env.docker.example .env.docker
rand() { openssl rand -hex "$1"; }
sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(rand 16)/" .env.docker
sed -i "s/^APP_DB_PASSWORD=.*/APP_DB_PASSWORD=$(rand 16)/" .env.docker
sed -i "s/^MIGRATOR_DB_PASSWORD=.*/MIGRATOR_DB_PASSWORD=$(rand 16)/" .env.docker
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$(rand 32)/" .env.docker
chmod 600 .env.docker
echo "Создан .env.docker со случайными паролями (в git не попадает)"
