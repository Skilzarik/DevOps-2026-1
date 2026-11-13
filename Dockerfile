# syntax=docker/dockerfile:1
# Образ приложения Music Store. Сборка из корня репозитория: docker build -t music-store:1.0.0 .
#
# Воспроизводимость: версия базового образа задана явно (не latest), зависимости ставятся
# строго из backend/requirements.txt (точные версии, make lock).
# Безопасность: в образе нет секретов и файлов .env, процесс работает от пользователя app (uid 10001).

ARG PYTHON_IMAGE=python:3.13-slim-bookworm

# ---------- Этап 1: виртуальное окружение с зависимостями ----------
FROM ${PYTHON_IMAGE} AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
COPY backend/requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install -r /tmp/requirements.txt

# ---------- Этап 2: рабочий образ (без компиляторов и кэшей сборки) ----------
FROM ${PYTHON_IMAGE} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv

# Приложение раздаёт интерфейс из ../frontend относительно рабочего каталога
WORKDIR /app/backend
COPY backend/app ./app
COPY backend/ale ./ale
COPY backend/alembic.ini ./alembic.ini
COPY frontend /app/frontend
# Код принадлежит root и доступен только на чтение: приложение не может его изменить
RUN chmod -R a+rX /app

USER 10001:10001
EXPOSE 8000

# Недоступность БД делает /health ответом 503, и контейнер получает статус unhealthy
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

# Exec-форма: uvicorn становится процессом PID 1 и сам получает SIGTERM от docker stop.
# Настройки приходят только из переменных окружения.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "20"]
