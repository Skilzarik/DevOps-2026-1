# Единый командный интерфейс проекта. Все команды запускаются из корня репозитория.
# Критический файл приёмки: ослаблять проверки нельзя (CONTRIBUTING.md).

SHELL := /bin/bash
PYTHON ?= python3
BACKEND := backend
VBIN := $(BACKEND)/venv/bin
# Подключает настройки тестовой БД (backend/.env.test) к одной команде
WITH_TEST_ENV = set -a; . ./$(BACKEND)/.env.test; set +a;

.DEFAULT_GOAL := help
.PHONY: help setup lock run test test-unit migrate-check quality format sast policy \
	    migrate backup restore mutate verify clean

help: ## Список команд
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

setup: ## Первоначальная настройка: окружение, зависимости, базы, миграции
	PYTHON=$(PYTHON) scripts/bootstrap.sh

lock: ## Зафиксировать точные версии зависимостей (requirements*.txt)
	PYTHON=$(PYTHON) scripts/lock.sh

run: ## Запустить приложение для разработки (http://localhost:8000)
	cd $(BACKEND) && venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

test: ## Все тесты + покрытие + отчёты (backend/reports/)
	$(WITH_TEST_ENV) cd $(BACKEND) && venv/bin/pytest

test-unit: ## Только быстрые unit-тесты (без базы данных)
	cd $(BACKEND) && venv/bin/pytest -m unit --no-cov

migrate-check: ## Проверка миграций на чистой и заполненной БД
	$(WITH_TEST_ENV) cd $(BACKEND) && venv/bin/pytest -m migrations --no-cov

quality: ## Линтер и проверка форматирования (ruff)
	cd $(BACKEND) && venv/bin/ruff check . && venv/bin/ruff format --check .

format: ## Автоматически исправить форматирование и импорты
	cd $(BACKEND) && venv/bin/ruff check --fix . && venv/bin/ruff format .

sast: ## Статический анализ безопасности (bandit), отчёт backend/reports/bandit.json
	mkdir -p $(BACKEND)/reports
	-cd $(BACKEND) && venv/bin/bandit -q -c pyproject.toml -r app ale -f json -o reports/bandit.json
	cd $(BACKEND) && venv/bin/bandit -q -c pyproject.toml -r app ale

policy: ## Запреты: пропуск тестов, снижение порогов, исключения, секреты, версии
	$(VBIN)/python scripts/check_policy.py

migrate: ## Применить миграции к рабочей БД (backend/.env)
	cd $(BACKEND) && venv/bin/alembic upgrade head

backup: ## Резервная копия рабочей БД в каталог backups/
	bash scripts/backup.sh

restore: ## Восстановление: make restore FILE=backups/<файл>.dump
	@test -n "$(FILE)" || { echo "Укажите файл: make restore FILE=backups/<файл>.dump"; exit 2; }
	bash scripts/restore.sh "$(FILE)"

mutate: ## Мутационная проверка: тесты должны замечать изменение условий
	$(WITH_TEST_ENV) $(VBIN)/python scripts/mutation_check.py

verify: policy quality sast test ## Полный набор обязательных проверок

clean: ## Удалить отчёты и кэши
	rm -rf $(BACKEND)/reports $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache $(BACKEND)/.coverage
