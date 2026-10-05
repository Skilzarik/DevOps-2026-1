#!/usr/bin/env bash
# 01_base.sh - базовая настройка сервера: запрет root по SSH, вход только по ключам, файрвол.
# Запускается на КАЖДОЙ машине от root:
#   sudo ROLE=app bash deploy/01_base.sh     # сервер приложения
#   sudo ROLE=db  bash deploy/01_base.sh     # сервер БД
# Скрипт можно запускать повторно.
set -euo pipefail

ROLE="${ROLE:?Укажите ROLE=app или ROLE=db}"
ADMIN_USER="${ADMIN_USER:-aurora}"          # администратор (вход по SSH-ключу)
ADMIN_NET="${ADMIN_NET:-192.168.56.0/24}"   # сеть, из которой разрешён SSH
APP_IP="${APP_IP:-192.168.56.10}"
DB_IP="${DB_IP:-192.168.56.20}"
APP_HOST="${APP_HOST:-app}"
DB_HOST_NAME="${DB_HOST_NAME:-db}"
APP_PORT="${APP_PORT:-8000}"

[ "$(id -u)" -eq 0 ] || { echo "Запустите через sudo" >&2; exit 1; }
case "$ROLE" in app|db) ;; *) echo "ROLE должен быть app или db" >&2; exit 1 ;; esac
id "$ADMIN_USER" >/dev/null 2>&1 || { echo "Нет пользователя $ADMIN_USER" >&2; exit 1; }

echo "== [1/5] Пакеты"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ufw openssh-server sudo

echo "== [2/5] Статический адрес (только при CONFIGURE_NET=1)"
if [ "${CONFIGURE_NET:-0}" = 1 ]; then
  IFACE="${IFACE:?Для CONFIGURE_NET=1 задайте IFACE, например enp0s8}"
  if [ "$ROLE" = app ]; then MY_IP="$APP_IP"; else MY_IP="$DB_IP"; fi
  cat > /etc/network/interfaces.d/lab-static <<NET
auto $IFACE
iface $IFACE inet static
    address $MY_IP/24
NET
  echo "Адрес записан. Примените вручную: systemctl restart networking"
else
  echo "пропущено"
fi

echo "== [3/5] Имена машин в /etc/hosts"
add_host() { grep -qE "^[[:space:]]*$1[[:space:]]+$2([[:space:]]|\$)" /etc/hosts || echo "$1 $2" >> /etc/hosts; }
add_host "$APP_IP" "$APP_HOST"
add_host "$DB_IP" "$DB_HOST_NAME"

echo "== [4/5] SSH: запрет root и паролей"
KEYS="$(getent passwd "$ADMIN_USER" | cut -d: -f6)/.ssh/authorized_keys"
if [ ! -s "$KEYS" ]; then
  echo "В $KEYS нет ключей. Сначала выполните с клиента ssh-copy-id и проверьте вход по ключу." >&2
  exit 1
fi
cat > /etc/ssh/sshd_config.d/10-hardening.conf <<'SSH'
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
SSH
sshd -t
systemctl reload ssh

if [ "$ROLE" = app ]; then
  echo "== Пользователь запуска приложения и каталог настроек"
  id appsvc >/dev/null 2>&1 || adduser --system --group --home /opt/myapp --shell /usr/sbin/nologin appsvc
  install -d -o root -g appsvc -m 750 /etc/myapp
fi

echo "== [5/5] Файрвол (ufw)"
ufw default deny incoming
ufw default allow outgoing
ufw allow from "$ADMIN_NET" to any port 22 proto tcp
if [ "$ROLE" = app ]; then
  ufw allow "${APP_PORT}/tcp"
else
  ufw allow from "$APP_IP" to any port 5432 proto tcp
fi
ufw --force enable
ufw status verbose

echo "Готово: 01_base.sh ($ROLE)"
