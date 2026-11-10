"""Чтение настроек: переменная окружения, затем backend/.env и backend/.env.test."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILES = [ROOT / "backend" / ".env", ROOT / "backend" / ".env.test"]


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def lookup(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    for path in ENV_FILES:
        value = read_env_file(path).get(name)
        if value:
            return value
    return None
