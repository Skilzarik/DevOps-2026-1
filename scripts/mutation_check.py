"""Мутационная проверка: тесты обязаны замечать изменение одного условия в логике.

Скрипт по очереди вносит в код приложения одну ошибку, запускает тесты и ожидает, что они
упадут (мутант «убит»). Если тесты прошли, мутант «выжил» - значит, проверка этого правила
слабая, и скрипт завершается с ошибкой. После каждой мутации файл восстанавливается.
Запуск из корня репозитория: make mutate (нужна тестовая БД, как для make test).
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

# (файл, исходный фрагмент, мутация, какое правило проверяем)
MUTANTS = [
    ("app/routes/sales.py", "if disc.stock < sale.quantity:", "if disc.stock <= sale.quantity:",
     "граница остатка: можно продать ровно остаток"),
    ("app/routes/sales.py", "if disc.stock < sale.quantity:", "if disc.stock > sale.quantity:",
     "продажа сверх остатка отклоняется"),
    ("app/routes/sales.py", "disc.stock -= sale.quantity", "disc.stock += sale.quantity",
     "остаток уменьшается после продажи"),
    ("app/routes/sales.py", "total_price = disc.price * sale.quantity",
     "total_price = disc.price + sale.quantity", "итоговая сумма = цена * количество"),
    ("app/routes/sales.py", "seller_id=current_user.id", "seller_id=None",
     "в продаже фиксируется продавец"),
    ("app/auth.py", 'if current_user.role != "admin":', 'if current_user.role == "admin":',
     "права администратора"),
    ("app/auth.py", "if user is None:", "if user is not None:",
     "токен несуществующего пользователя отклоняется"),
    ("app/routes/discs.py", "if disc.sales:", "if not disc.sales:",
     "нельзя удалить диск с продажами"),
    ("app/routes/discs.py", "if restock_data.quantity <= 0:", "if restock_data.quantity < 0:",
     "граница пополнения: 0 недопустим"),
    ("app/routes/discs.py", "disc.stock += restock_data.quantity",
     "disc.stock -= restock_data.quantity", "пополнение увеличивает остаток"),
    ("app/routes/musicians.py", "if has_sales:", "if not has_sales:",
     "нельзя удалить исполнителя с проданными дисками"),
    ("app/routes/users.py", "if db_user:", "if not db_user:",
     "имя пользователя уникально"),
    ("app/routes/users.py", "or not auth.verify_password(", "or auth.verify_password(",
     "вход с неверным паролем запрещён"),
    ("app/schemas.py", "price: float = Field(gt=0", "price: float = Field(ge=0",
     "цена диска строго больше нуля"),
    ("app/schemas.py", "quantity: int = Field(gt=0", "quantity: int = Field(ge=0",
     "количество в продаже больше нуля"),
]

PYTEST = [sys.executable, "-m", "pytest", "-x", "-q", "-o", "addopts=", "-p", "no:cacheprovider"]


def run_tests() -> bool:
    result = subprocess.run(PYTEST, cwd=BACKEND, capture_output=True, text=True, check=False)
    return result.returncode == 0


def main() -> int:
    print("Базовый прогон тестов без мутаций...")
    if not run_tests():
        print("Тесты падают и без мутаций: сначала добейтесь зелёного make test")
        return 2

    survived = []
    for rel_path, old, new, rule in MUTANTS:
        path = BACKEND / rel_path
        original = path.read_bytes()
        text = original.decode("utf-8")
        if text.count(old) != 1:
            print(f"Шаблон мутации устарел ({rel_path}: {old!r} встречается {text.count(old)} раз)")
            return 2
        try:
            path.write_bytes(text.replace(old, new).encode("utf-8"))
            killed = not run_tests()
        finally:
            path.write_bytes(original)
        status = "УБИТ    " if killed else "ВЫЖИЛ   "
        print(f"{status} {rel_path}: {old}  ->  {new}   [{rule}]")
        if not killed:
            survived.append((rel_path, rule))

    total = len(MUTANTS)
    print(f"\nУбито мутантов: {total - len(survived)} из {total}")
    if survived:
        print("Выжившие мутанты (тесты их не заметили):")
        for rel_path, rule in survived:
            print(f"  - {rel_path}: {rule}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
