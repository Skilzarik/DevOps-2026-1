"""Печатает команды export PG* для pg_dump/pg_restore из строки подключения.

Пароль передаётся через окружение, а не через аргументы командной строки,
поэтому не виден в списке процессов. Использование: eval "$(python pgenv.py [ИМЯ_ПЕРЕМЕННОЙ])"
"""

import shlex
import sys

from _env import lookup
from sqlalchemy.engine import make_url


def main() -> None:
    var = sys.argv[1] if len(sys.argv) > 1 else "DATABASE_URL"
    url = lookup(var)
    if not url:
        sys.exit(f"{var} не задан (переменная окружения или backend/.env)")
    parsed = make_url(url)
    pairs = {
        "PGHOST": parsed.host or "localhost",
        "PGPORT": str(parsed.port or 5432),
        "PGUSER": parsed.username or "",
        "PGPASSWORD": parsed.password or "",
        "PGDATABASE": parsed.database or "",
    }
    for key, value in pairs.items():
        print(f"export {key}={shlex.quote(value)}")


if __name__ == "__main__":
    main()
