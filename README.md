# Музыкальный магазин 
Информационная система для учёта музыкантов, музыкальных дисков, управления остатками и регистрации продаж.   
---

## Быстрый старт

### 1. Предварительные требования

На компьютере должны быть установлены:
- **Python 3.10+**
- **PostgreSQL 14+**
- **Git**

### 2. Клонирование и подготовка окружения

Выполните следующие команды в терминале:

```bash
# 1. Клонируйте репозиторий и перейдите в него
git clone https://github.com/Skilzarik/DevOps-2026-1.git
cd music-store

# 2. Перейдите в директорию backend
cd backend

# 3. Создайте виртуальное окружение
python -m venv venv

# 4. Активируйте виртуальное окружение
# Для Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Для macOS/Linux:
source venv/bin/activate

# 5. Установите зависимости
pip install -r requirements.txt
```

### 3. Настройка базы данных (PostgreSQL)

1. Убедитесь, что служба PostgreSQL запущена.
2. Создайте базу данных с именем `music_store`. Это можно сделать через **pgAdmin** или через консоль **psql**:

```sql
CREATE DATABASE music_store;
```

3. В папке `backend` создайте файл `.env` (или скопируйте `.env.example` и переименуйте его).
4. Откройте `.env` и укажите ваши реальные данные для подключения к PostgreSQL:

```env
# Замените 'postgres' и 'your_password' на ваш логин и пароль от PostgreSQL
DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/music_store
SECRET_KEY=your-super-secret-key-for-jwt
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

> **Важно:** используется драйвер `psycopg` (v3), поэтому в URL указан префикс `postgresql+psycopg://`.

### 4. Применение миграций базы данных

Проект использует **Alembic** для управления схемой БД. Чтобы создать все необходимые таблицы (`users`, `musicians`, `discs`, `sales`), выполните в папке `backend`:

```bash
alembic upgrade head
```

### 5. Запуск приложения

Убедитесь, что виртуальное окружение активировано и вы находитесь в папке `backend`. Запустите сервер разработки:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

При успешном запуске вы увидите сообщение:
```
INFO:     Application startup complete.
```

---

## Доступ к приложению

После запуска сервера откройте браузер и перейдите по следующим адресам:

| Ресурс              | URL                               | Описание                                          |
|---------------------|-----------------------------------|---------------------------------------------------|
| **Веб-интерфейс**   | http://localhost:8000/            | Основной интерфейс для работы пользователей       |
| **API Документация**| http://localhost:8000/docs        | Интерактивная документация Swagger UI             |
| **Проверка здоровья**| http://localhost:8000/health     | Эндпоинт для проверки статуса БД и приложения     |

---

## Тестирование функционала

Для быстрой проверки работы системы выполните следующий сценарий:

1. Откройте http://localhost:8000/
2. Перейдите на вкладку **«Регистрация»**.
3. Создайте пользователя с ролью **Администратор** (`admin`).
4. Войдите в систему под созданным пользователем.
5. В разделе **«Музыканты»** добавьте нового исполнителя.
6. В разделе **«Каталог дисков»** добавьте диск, привязав его к созданному музыканту (укажите цену и остаток).
7. Попробуйте оформить продажу этого диска. Убедитесь, что остаток уменьшился.
8. *(Опционально)* Выйдите, зарегистрируйте пользователя с ролью **Продавец** (`seller`) и убедитесь, что у него нет кнопок «Добавить», «Удалить» и «Пополнить» в каталоге.

---

## Стек технологий

- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2.0, Pydantic, Alembic
- **Database:** PostgreSQL 15+, драйвер `psycopg` (v3)
- **Auth:** JWT (JSON Web Tokens), `passlib` + `bcrypt`
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (Fetch API)
- **DevOps:** Git, Conventional Commits, `.env` конфигурация

---

## Структура проекта

```text
.
├── backend/
│   ├── alembic/            # Скрипты миграций базы данных
│   ├── app/
│   │   ├── routes/         # Эндпоинты API (users, musicians, discs, sales)
│   │   ├── auth.py         # Логика JWT и хеширования паролей
│   │   ├── database.py     # Настройка подключения к БД и сессии
│   │   ├── main.py         # Точка входа FastAPI приложения
│   │   ├── models.py       # SQLAlchemy модели (схема БД)
│   │   └── schemas.py      # Pydantic схемы для валидации данных
│   ├── .env                # Переменные окружения (не коммитится в Git)
│   ├── .env.example        # Пример переменных окружения
│   └── requirements.txt    # Зависимости Python
├── frontend/
│   ├── index.html          # Разметка веб-интерфейса
│   ├── style.css           # Стили
│   └── script.js           # Клиентская логика и запросы к API
├── .gitignore              # Правила игнорирования файлов для Git
├── CONTRIBUTING.md         # Правила внесения изменений в проект
└── README.md               # Этот файл
```
## Развёртывание на Linux (без контейнеров)

### Схема

| Машина | Адрес | Роль |
|---|---|---|
| app | 192.168.56.10 | приложение (FastAPI + uvicorn, systemd-служба `myapp`) |
| db | 192.168.56.20 | PostgreSQL 17 |

ОС: Debian 13 без графического интерфейса (только SSH server и standard system utilities).
Клиент (браузер) обращается к приложению на порт 8000.

### Требования безопасности

1. Приложение запускается только от системного пользователя `appsvc` (без входа в систему, оболочка `nologin`). Запуск от root запрещён.
2. Лишние порты не открываются:
   - app: 22/tcp (только из 192.168.56.0/24) и 8000/tcp;
   - db: 22/tcp (только из 192.168.56.0/24) и 5432/tcp (только с 192.168.56.10).
   PostgreSQL слушает только `localhost` и 192.168.56.20.
3. Пароли и ключи в репозитории не хранятся. Настройки лежат на сервере в
   `/etc/myapp/myapp.env` (владелец `root:appsvc`, права 640). В репозитории только `.env.example`;
   `.env`, `*.env` и `venv/` внесены в `.gitignore`.
4. Вход по SSH под root и вход по паролю отключены, используются только ключи.
5. Права в БД минимальны: пользователь приложения `appuser` имеет только SELECT/INSERT/UPDATE/DELETE
   на таблицы и не может создавать или удалять объекты. Схему создаёт отдельная роль `migrator`.
6. Код в `/opt/myapp` принадлежит `root:appsvc` (права 750): приложение его читает, но не изменяет.

### Порядок развёртывания

**1. Обе машины: SSH и пользователи**

```bash
# с клиента
ssh-copy-id -i ~/.ssh/id_ed25519.pub aurora@192.168.56.10
ssh-copy-id -i ~/.ssh/id_ed25519.pub aurora@192.168.56.20

# на каждой машине (после проверки входа по ключу)
sudo tee /etc/ssh/sshd_config.d/10-hardening.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
EOF
sudo sshd -t && sudo systemctl reload ssh
```

Статический адрес задаётся в `/etc/network/interfaces`:

```
auto enp0s8
iface enp0s8 inet static
    address 192.168.56.10/24     # на db: 192.168.56.20/24
```

**2. db: PostgreSQL**

```bash
sudo apt update && sudo apt install -y postgresql
# в /etc/postgresql/17/main/postgresql.conf:
#   listen_addresses = 'localhost,192.168.56.20'
# в конец /etc/postgresql/17/main/pg_hba.conf:
#   host  music_store  appuser   192.168.56.10/32  scram-sha-256
#   host  music_store  migrator  192.168.56.10/32  scram-sha-256

APPPASS=$(openssl rand -hex 16)      # сохранить для /etc/myapp/myapp.env на app
MIGPASS=$(openssl rand -hex 16)      # нужен только для первичного создания таблиц
sudo -u postgres psql <<EOF
CREATE ROLE migrator LOGIN PASSWORD '$MIGPASS';
CREATE ROLE appuser LOGIN PASSWORD '$APPPASS';
CREATE DATABASE music_store OWNER migrator;
REVOKE ALL ON DATABASE music_store FROM PUBLIC;
GRANT CONNECT ON DATABASE music_store TO appuser;
\c music_store
GRANT USAGE ON SCHEMA public TO appuser;
ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO appuser;
ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO appuser;
EOF
echo "appuser: $APPPASS"; echo "migrator: $MIGPASS"     # записать и очистить историю терминала
unset APPPASS MIGPASS
sudo systemctl restart postgresql
```

**3. app: пользователь, код, зависимости**

```bash
sudo apt install -y python3-venv git libpq5
sudo adduser --system --group --home /opt/myapp --shell /usr/sbin/nologin appsvc
sudo mkdir -p /etc/myapp && sudo chown root:appsvc /etc/myapp && sudo chmod 750 /etc/myapp
sudo git clone https://github.com/Skilzarik/DevOps-2026-1.git /opt/myapp
sudo python3 -m venv /opt/myapp/venv
sudo /opt/myapp/venv/bin/pip install -r /opt/myapp/backend/requirements.txt
sudo chown -R root:appsvc /opt/myapp && sudo chmod -R u=rwX,g=rX,o= /opt/myapp
```

**4. app: первичное создание таблиц (один раз, под `migrator`)**

Приложение создаёт таблицы само, но `appuser` на это прав не имеет, поэтому первый запуск делается под `migrator`.
Пароль вводится интерактивно и нигде не сохраняется:

```bash
read -s -p "Пароль migrator: " M; echo
sudo env M="$M" sh -c 'cd /opt/myapp/backend && \
  DATABASE_URL="postgresql+psycopg://migrator:$M@192.168.56.20:5432/music_store" \
  SECRET_KEY=tmp /opt/myapp/venv/bin/python -c \
  "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"'
unset M
```

**5. app: настройки отдельно от кода**

```bash
read -s -p "Пароль appuser: " P; echo
sudo tee /etc/myapp/myapp.env >/dev/null <<EOF
DATABASE_URL=postgresql+psycopg://appuser:$P@192.168.56.20:5432/music_store
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
APP_PORT=8000
EOF
unset P
sudo chown root:appsvc /etc/myapp/myapp.env && sudo chmod 640 /etc/myapp/myapp.env
```

**6. app: systemd-служба**

Файл `/etc/systemd/system/myapp.service`:

```ini
[Unit]
Description=Music Store (FastAPI/uvicorn)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=appsvc
Group=appsvc
WorkingDirectory=/opt/myapp/backend
EnvironmentFile=/etc/myapp/myapp.env
ExecStart=/opt/myapp/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}
Restart=on-failure
RestartSec=3
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now myapp
```

Управление службой: `sudo systemctl start|stop|restart|status myapp`.
Автозапуск при загрузке включён (`enable`), автоперезапуск после аварии настроен
параметрами `Restart=on-failure` и `RestartSec=3`.

**7. Firewall (ufw)**

```bash
# db
sudo apt install -y ufw
sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow from 192.168.56.0/24 to any port 22 proto tcp
sudo ufw allow from 192.168.56.10 to any port 5432 proto tcp
sudo ufw enable

# app
sudo apt install -y ufw
sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow from 192.168.56.0/24 to any port 22 proto tcp
sudo ufw allow 8000/tcp
sudo ufw enable
```

Правило для SSH добавляется до `ufw enable`.

### Обновление приложения

```bash
sudo git -C /opt/myapp pull
sudo chown -R root:appsvc /opt/myapp && sudo chmod -R u=rwX,g=rX,o= /opt/myapp
sudo systemctl restart myapp
```

### Проверка

| Что проверяем | Команда | Ожидаемый результат |
|---|---|---|
| Служба работает | `systemctl is-active myapp` | `active` |
| Автозапуск включён | `systemctl is-enabled myapp` | `enabled` |
| Процесс не от root | `ps -o user= -p $(systemctl show -p MainPID --value myapp)` | `appsvc` |
| Приложение и БД | `curl -s http://localhost:8000/health` | `"status":"ok"` |
| Автоперезапуск | `sudo kill -9 $(systemctl show -p MainPID --value myapp)`, через 4 с `systemctl is-active myapp` | `active`, новый PID |
| Порт приложения | `sudo ss -tlnp \| grep 8000` | слушает uvicorn |
| Журнал | `journalctl -u myapp -n 50 --no-pager` | записи службы |
| БД недоступна посторонним | с клиента: `nc -vz -w3 192.168.56.20 5432` | таймаут |
| БД доступна приложению | с app: `nc -vz 192.168.56.20 5432` | `succeeded` |
| Минимальные права | с app: `psql -h 192.168.56.20 -U appuser music_store -c 'DROP TABLE users;'` | `must be owner of table` |
| SSH под root закрыт | `ssh root@192.168.56.10` | `Permission denied` |