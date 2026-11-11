"""Проверка организационных правил (CONTRIBUTING.md, раздел 2). Входит в make verify.

Ловит то, что запрещено делать «только ради прохождения проверки»: удалять или отключать
тесты, снижать пороги, добавлять исключения анализаторов без обоснования, хранить секреты
в репозитории, оставлять зависимости без точных версий.
"""

import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
errors: list[str] = []
checks = 0


def fail(message: str) -> None:
    errors.append(message)


def read_baseline() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in (ROOT / "quality-baseline.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            values[key.strip()] = int(value)
    return values


def python_files() -> list[Path]:
    skip = {"venv", "__pycache__", "reports", "mutants"}
    return [p for p in BACKEND.rglob("*.py") if not skip & set(p.relative_to(BACKEND).parts)]


def check_no_disabled_tests_or_unjustified_exceptions() -> None:
    skip_pattern = re.compile(
        r"pytest\.mark\.(skip|skipif|xfail)|pytest\.(skip|xfail)\(|unittest\.skip"
    )
    justified = re.compile(r"#\s*justified:\s*\S.{9,}")
    exception_pattern = re.compile(r"#\s*(noqa|nosec)")
    reason = re.compile(r"--\s+\S.{5,}")
    for path in python_files():
        rel = path.relative_to(ROOT)
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "tests" in path.parts and skip_pattern.search(line) and not justified.search(line):
                fail(f"{rel}:{number}: skip/xfail без обоснования ('# justified: <причина>')")
            if exception_pattern.search(line) and not reason.search(line):
                fail(f"{rel}:{number}: noqa/nosec без обоснования ('-- <причина>')")


def check_thresholds_and_config(baseline: dict[str, int]) -> None:
    config = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    floor = config["tool"]["coverage"]["report"]["fail_under"]
    if floor < baseline["COVERAGE_MIN"]:
        fail(f"fail_under={floor} ниже зафиксированного минимума {baseline['COVERAGE_MIN']}")
    lint = config["tool"]["ruff"].get("lint", {})
    ignores = len(lint.get("ignore", [])) + sum(
        len(v) for v in lint.get("per-file-ignores", {}).values()
    )
    if ignores > baseline["RUFF_IGNORES"]:
        fail(f"В ruff добавлены исключения ({ignores} > {baseline['RUFF_IGNORES']})")
    if "--cov" not in config["tool"]["pytest"]["ini_options"].get("addopts", ""):
        fail("В pytest addopts убрано измерение покрытия (--cov)")
    if config["tool"].get("bandit", {}).get("skips"):
        fail("В bandit добавлены skips: исключения анализатора запрещены без обоснования")


def check_tests_not_removed(baseline: dict[str, int]) -> None:
    count = sum(
        len(re.findall(r"^\s*def test_", p.read_text(encoding="utf-8"), re.M))
        for p in (BACKEND / "tests").glob("test_*.py")
    )
    if count < baseline["TESTS_MIN"]:
        fail(f"Тестов стало меньше зафиксированного ({count} < {baseline['TESTS_MIN']})")


def check_pinned_requirements() -> None:
    pinned = re.compile(r"^[A-Za-z0-9_.\-]+(\[[A-Za-z0-9_,\-]+\])?==[^=<>~!\s;]+(\s*;.*)?$")
    for name in ("requirements.txt", "requirements-dev.txt"):
        path = BACKEND / name
        if not path.exists():
            fail(f"{name} отсутствует: выполните make lock")
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if line and not line.startswith("#") and not pinned.match(line):
                fail(f"backend/{name}:{number}: версия не зафиксирована точно (==): {line}")


def check_no_secrets_in_repo() -> None:
    url_with_password = re.compile(r"postgresql(\+\w+)?://[^:\s/$<{]+:[^@\s$<{]+@")
    targets = [BACKEND / "alembic.ini", ROOT / "Makefile"]
    targets += [p for p in python_files() if "tests" not in p.parts]
    targets += list((ROOT / "scripts").glob("*"))
    for path in targets:
        if path.is_file() and path.name != "check_policy.py":
            text = path.read_text(encoding="utf-8", errors="ignore")
            if url_with_password.search(text):
                fail(f"{path.relative_to(ROOT)}: строка подключения с паролем в открытом виде")
    if (ROOT / ".git").exists():
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.splitlines()
        for name in tracked:
            base = Path(name).name
            if (base == ".env" or base.endswith(".env") or base.startswith(".env.")) and not (
                base.endswith(".example")
            ):
                fail(f"{name}: файл с настройками не должен находиться в git")


def check_traceability(baseline: dict[str, int]) -> None:
    path = ROOT / "docs" / "TRACEABILITY.md"
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and re.fullmatch(r"R\d+", cells[0]):
            rows.append(cells)
    covered = 0
    for cells in rows:
        refs = re.findall(r"(\w+\.py)::(test_\w+)", cells[2])
        valid = True
        for file_name, test_name in refs:
            test_file = BACKEND / "tests" / file_name
            if not test_file.exists() or f"def {test_name}(" not in test_file.read_text(
                encoding="utf-8"
            ):
                fail(f"TRACEABILITY.md: {cells[0]} ссылается на несуществующий тест {file_name}::{test_name}")
                valid = False
        if refs and valid:
            covered += 1
    percent = 100 * covered // max(len(rows), 1)
    if percent < baseline["TRACEABILITY_MIN"]:
        fail(f"Покрыто требований ТЗ: {percent}% (< {baseline['TRACEABILITY_MIN']}%)")
    print(f"  требований ТЗ: {len(rows)}, покрыто тестами: {covered} ({percent}%)")


def main() -> int:
    global checks
    baseline = read_baseline()
    for check in (
        check_no_disabled_tests_or_unjustified_exceptions,
        lambda: check_thresholds_and_config(baseline),
        lambda: check_tests_not_removed(baseline),
        check_pinned_requirements,
        check_no_secrets_in_repo,
        lambda: check_traceability(baseline),
    ):
        check()
        checks += 1
    if errors:
        print("policy: НАРУШЕНИЯ")
        for message in errors:
            print(f"  - {message}")
        return 1
    print(f"policy: OK ({checks} проверок)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
