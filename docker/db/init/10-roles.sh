#!/bin/sh
# Выполняется ОДИН раз при создании пустого тома БД (механизм docker-entrypoint-initdb.d).
# Создаёт роли так же, как на сервере в лабораторной 2:
#   migrator - владелец базы и схемы, нужен только для миграций;
#   appuser  - приложение, только SELECT/INSERT/UPDATE/DELETE.
# Пароли приходят из переменных окружения, в образе и в репозитории их нет.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -v app_pw="$APP_DB_PASSWORD" -v mig_pw="$MIGRATOR_DB_PASSWORD" <<'SQL'
CREATE ROLE migrator LOGIN PASSWORD :'mig_pw';
CREATE ROLE appuser LOGIN PASSWORD :'app_pw';
CREATE DATABASE music_store OWNER migrator;
REVOKE ALL ON DATABASE music_store FROM PUBLIC;
GRANT CONNECT ON DATABASE music_store TO appuser;
\connect music_store
GRANT USAGE ON SCHEMA public TO appuser;
ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO appuser;
ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO appuser;
SQL
