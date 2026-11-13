#!/usr/bin/env python3
"""Одноразовые правки для лабораторной 4 (безопасно запускать повторно).

1. backend/app/main.py: идентификатор экземпляра в заголовке X-Instance-ID каждого ответа.
2. backend/tests/test_service.py: тест этого поведения.
3. CONTRIBUTING.md: раздел о контейнерных правилах.
4. quality-baseline.txt: порог числа тестов +1 (добавлен тест); .gitignore: файл .env.docker.
После запуска выполните `make format`, затем `make verify`.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def eol_of(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def patch_main() -> None:
    path = ROOT / "backend" / "app" / "main.py"
    text = path.read_text(encoding="utf-8")
    if "INSTANCE_ID" in text:
        print("main.py: уже изменён")
        return
    eol = eol_of(text)
    anchor = "app.include_router(sales.router)"
    if anchor not in text:
        raise SystemExit("main.py: не найдена строка app.include_router(sales.router)")
    block = eol.join(
        [
            anchor,
            "",
            'INSTANCE_ID = os.environ.get("INSTANCE_ID") or socket.gethostname()',
            "",
            "",
            '@app.middleware("http")',
            "async def add_instance_id_header(request, call_next):",
            '    """Показывает, какой экземпляр приложения обработал запрос (Лаб. 4)."""',
            "    response = await call_next(request)",
            '    response.headers["X-Instance-ID"] = INSTANCE_ID',
            "    return response",
        ]
    )
    text = text.replace(anchor, block, 1)
    text = f"import os{eol}import socket{eol}{eol}" + text
    path.write_text(text, encoding="utf-8")
    print("main.py: добавлен заголовок X-Instance-ID")


def patch_tests() -> bool:
    path = ROOT / "backend" / "tests" / "test_service.py"
    text = path.read_text(encoding="utf-8")
    if "test_response_contains_instance_id_header" in text:
        print("test_service.py: тест уже есть")
        return False
    eol = eol_of(text)
    addition = eol.join(
        [
            "",
            "",
            "def test_response_contains_instance_id_header(client):",
            "    from app.main import INSTANCE_ID",
            "",
            '    response = client.get("/health")',
            "    assert INSTANCE_ID",
            '    assert response.headers["X-Instance-ID"] == INSTANCE_ID',
            "",
        ]
    )
    path.write_text(text.rstrip("\r\n") + eol + addition, encoding="utf-8")
    print("test_service.py: добавлен тест")
    return True


def patch_baseline() -> None:
    path = ROOT / "quality-baseline.txt"
    text = path.read_text(encoding="utf-8")
    match = re.search(r"TESTS_MIN=(\d+)", text)
    if not match:
        raise SystemExit("quality-baseline.txt: не найден TESTS_MIN")
    new_value = int(match.group(1)) + 1
    path.write_text(text.replace(match.group(0), f"TESTS_MIN={new_value}", 1), encoding="utf-8")
    print(f"quality-baseline.txt: TESTS_MIN={new_value}")


def patch_gitignore() -> None:
    path = ROOT / ".gitignore"
    text = path.read_text(encoding="utf-8")
    if ".env.docker\n" in text.replace(".env.docker.example", "") or text.rstrip().endswith(".env.docker"):
        print(".gitignore: .env.docker уже исключён")
        return
    path.write_text(
        text.rstrip("\n") + "\n\n# Лаб. 4: настройки контейнерного окружения (пароли)\n.env.docker\n",
        encoding="utf-8",
    )
    print(".gitignore: добавлен .env.docker")


def patch_contributing() -> None:
    path = ROOT / "CONTRIBUTING.md"
    text = path.read_text(encoding="utf-8")
    if "Контейнерное окружение (Лаб. 4)" in text:
        print("CONTRIBUTING.md: раздел уже есть")
        return
    marker = "## 3. Стиль коммитов"
    if marker not in text:
        raise SystemExit("CONTRIBUTING.md: не найден раздел '## 3. Стиль коммитов'")
    eol = eol_of(text)
    section = """## 2а. Контейнерное окружение (Лаб. 4)

Команды: `make up`, `make down`, `make container-check`, `make container-backup`,
`make container-restore FILE=...`. Описание: [docs/CONTAINERS.md](docs/CONTAINERS.md).

Изменения `Dockerfile`, `compose.yaml`, `docker/` разрешено вносить в Pull Request только после
успешного `make container-check` (его результат прикладывается к PR).

**Запрещено:**

- тег `latest` и образы без явного тега;
- запуск процессов от root (в Dockerfile обязателен `USER` с непривилегированным пользователем);
- секреты в образе, в `Dockerfile` и в `compose.yaml` (только переменные окружения из `.env.docker`,
  которого нет в git);
- отключение healthcheck (`disable: true`, `HEALTHCHECK NONE`);
- публикация портов, кроме порта nginx: порты БД и приложения наружу не открываются;
- контейнеры без лимитов памяти и процессора; `privileged`, `network_mode: host`, монтирование `docker.sock`.

Эти правила проверяет `scripts/check_container_policy.py` (входит в `make container-check`).

**Критические файлы приёмки:** `Dockerfile`, `.dockerignore`, `compose.yaml`, `docker/**`,
`scripts/container_check.sh`, `scripts/check_container_policy.py`. Любое их изменение выделяется в описании PR.

---

""".replace("\n", eol)
    path.write_text(text.replace(marker, section + marker, 1), encoding="utf-8")
    print("CONTRIBUTING.md: добавлен раздел 2а")


if __name__ == "__main__":
    patch_main()
    if patch_tests():
        patch_baseline()
    patch_contributing()
    patch_gitignore()
