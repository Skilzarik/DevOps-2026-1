#!/usr/bin/env python3
"""Проверка контейнерных правил (CONTRIBUTING.md, раздел 2а). Входит в make container-check.

Запрещено: тег latest и образы без тега, запуск от root, секреты в образе, отключение
healthcheck, публикация лишних портов, контейнеры без лимитов ресурсов.

Без аргументов проверяет файлы (Dockerfile, .dockerignore, compose.yaml).
С --config <json> дополнительно проверяет итоговую конфигурацию `docker compose config --format json`.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
SECRET_NAME = re.compile(r"(PASSWORD|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY)", re.I)
ENTRY_SERVICE = "nginx"
ENTRY_TARGET_PORT = 8080


def fail(message: str) -> None:
    errors.append(message)


def image_problem(ref: str) -> str | None:
    ref = ref.strip()
    if not ref:
        return "пустое имя образа"
    if "@sha256:" in ref:
        return None
    last = ref.rsplit("/", 1)[-1]
    if ":" not in last:
        return f"образ без тега ({ref}) означает latest"
    if last.split(":", 1)[1].lower() == "latest":
        return f"тег latest запрещён ({ref})"
    return None


def check_dockerfile() -> None:
    path = ROOT / "Dockerfile"
    if not path.exists():
        fail("Dockerfile отсутствует")
        return
    text = re.sub(r"\\\n", " ", path.read_text(encoding="utf-8"))
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]

    args: dict[str, str] = {}
    stages: set[str] = set()
    users: list[str] = []
    has_healthcheck = False

    for line in lines:
        keyword = line.split(None, 1)[0].upper()
        if keyword == "ARG":
            match = re.match(r"ARG\s+(\w+)(?:=(.*))?", line, re.I)
            if match:
                name, value = match.group(1), (match.group(2) or "").strip().strip('"')
                args[name] = value
                if SECRET_NAME.search(name) and value:
                    fail(f"Dockerfile: секрет в ARG {name}")
        elif keyword == "FROM":
            match = re.match(r"FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?", line, re.I)
            if match:
                ref = re.sub(r"\$\{(\w+)\}", lambda m: args.get(m.group(1), ""), match.group(1))
                if ref not in stages:
                    problem = image_problem(ref)
                    if problem:
                        fail(f"Dockerfile: {problem}")
                if match.group(2):
                    stages.add(match.group(2))
        elif keyword == "ENV":
            for name, value in re.findall(r'(\w+)=("[^"]*"|\S*)', line):
                if SECRET_NAME.search(name) and value.strip('"'):
                    fail(f"Dockerfile: секрет в ENV {name}")
        elif keyword == "USER":
            users.append(line.split(None, 1)[1].strip())
        elif keyword == "HEALTHCHECK":
            if line.split(None, 1)[1].strip().upper().startswith("NONE"):
                fail("Dockerfile: HEALTHCHECK NONE отключает проверку состояния")
            else:
                has_healthcheck = True
        elif keyword in ("COPY", "ADD") and re.search(r"\.env\b", line):
            fail(f"Dockerfile: в образ копируется файл настроек: {line}")
        elif keyword in ("CMD", "ENTRYPOINT") and not line.split(None, 1)[1].lstrip().startswith("["):
            fail(f"Dockerfile: {keyword} в shell-форме мешает доставке сигналов (нужна exec-форма)")

    if not users:
        fail("Dockerfile: нет инструкции USER, процесс работал бы от root")
    elif users[-1].split(":")[0] in ("root", "0"):
        fail("Dockerfile: последняя инструкция USER задаёт root")
    if not has_healthcheck:
        fail("Dockerfile: нет HEALTHCHECK")


def check_dockerignore() -> None:
    path = ROOT / ".dockerignore"
    if not path.exists():
        fail(".dockerignore отсутствует")
        return
    content = path.read_text(encoding="utf-8")
    for required in (".git", ".env", "venv"):
        if required not in content:
            fail(f".dockerignore: не исключено '{required}'")


def check_compose_text() -> None:
    path = ROOT / "compose.yaml"
    if not path.exists():
        fail("compose.yaml отсутствует")
        return
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        code = line.split("#", 1)[0]
        if re.search(r"privileged:\s*true", code):
            fail(f"compose.yaml:{number}: privileged запрещён")
        if re.search(r"network_mode:\s*host", code):
            fail(f"compose.yaml:{number}: network_mode host запрещён")
        if "docker.sock" in code:
            fail(f"compose.yaml:{number}: монтирование docker.sock запрещено")
        if re.search(r"disable:\s*true", code):
            fail(f"compose.yaml:{number}: healthcheck отключать запрещено")
        if re.search(r"^\s*image:\s*\S+", code) and "${" not in code:
            problem = image_problem(code.split("image:", 1)[1])
            if problem:
                fail(f"compose.yaml:{number}: {problem}")
        match = re.match(r"^\s*(\w*(?:PASSWORD|SECRET)\w*)\s*:\s*(.+)$", code)
        if match and "${" not in match.group(2):
            fail(f"compose.yaml:{number}: значение {match.group(1)} должно браться из переменной ${{...}}")
    if not (ROOT / "docker" / "nginx" / "default.conf").exists():
        fail("docker/nginx/default.conf отсутствует")


def service_networks(service: dict) -> list[str]:
    networks = service.get("networks") or []
    return list(networks.keys()) if isinstance(networks, dict) else list(networks)


def check_config(config: dict) -> None:
    services = config.get("services", {})
    for name, svc in services.items():
        problem = image_problem(svc.get("image", ""))
        if problem:
            fail(f"сервис {name}: {problem}")
        if svc.get("privileged"):
            fail(f"сервис {name}: privileged запрещён")
        if str(svc.get("user", "")).split(":")[0] in ("root", "0"):
            fail(f"сервис {name}: запуск от root запрещён")
        if (svc.get("healthcheck") or {}).get("disable"):
            fail(f"сервис {name}: healthcheck отключён")
        limits = ((svc.get("deploy") or {}).get("resources") or {}).get("limits") or {}
        if not limits.get("memory") or not limits.get("cpus"):
            fail(f"сервис {name}: не заданы лимиты памяти и процессора")
        ports = svc.get("ports") or []
        if name != ENTRY_SERVICE and ports:
            fail(f"сервис {name}: публикует порты наружу ({len(ports)}), разрешено только nginx")
        if name == ENTRY_SERVICE:
            for port in ports:
                if int(port.get("target", 0)) != ENTRY_TARGET_PORT:
                    fail(f"nginx публикует лишний порт {port.get('target')}")
        for volume in svc.get("volumes") or []:
            source = volume.get("source", "") if isinstance(volume, dict) else volume
            if "docker.sock" in str(source):
                fail(f"сервис {name}: монтирует docker.sock")
        if name != ENTRY_SERVICE and "edge" in service_networks(svc):
            fail(f"сервис {name}: подключён к внешней сети edge")

    if not (config.get("networks", {}).get("backend") or {}).get("internal"):
        fail("сеть backend должна быть internal")

    instances = [n for n, s in services.items() if "INSTANCE_ID" in (s.get("environment") or {})]
    if len(instances) < 2:
        fail("нужно не менее двух экземпляров приложения (переменная INSTANCE_ID)")

    for name, svc in services.items():
        for key, value in (svc.get("environment") or {}).items():
            if SECRET_NAME.search(key) and str(value) in ("", "CHANGE_ME", "changeme", "password"):
                fail(f"сервис {name}: небезопасное значение {key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="JSON из docker compose config --format json")
    args = parser.parse_args()

    check_dockerfile()
    check_dockerignore()
    check_compose_text()
    if args.config:
        check_config(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if errors:
        print("container-policy: НАРУШЕНИЯ")
        for message in errors:
            print(f"  - {message}")
        return 1
    print("container-policy: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
