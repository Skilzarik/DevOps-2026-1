"""Резервное копирование и восстановление (Лаб. 3, п. 11-12)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]


def _run_script(name: str, *args: str, backup_dir: Path) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "BACKUP_DIR": str(backup_dir),
        "PY": sys.executable,
        "ASSUME_YES": "1",
    }
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / name), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{name} завершился с ошибкой:\n{result.stdout}\n{result.stderr}"
    return result


def _snapshot(engine) -> dict:
    """Состояние данных. Соединение закрывается сразу, чтобы не блокировать восстановление."""
    with engine.connect() as conn:
        counts = {
            table: conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in ("users", "musicians", "discs", "sales")
        }
        counts["stock"] = conn.execute(text("SELECT stock FROM discs")).scalar_one()
    return counts


def test_backup_then_restore_recovers_damaged_data(
    client, admin_headers, musician, disc, clean_db, tmp_path
):
    sale = client.post(
        "/sales/", json={"disc_id": disc["id"], "quantity": 2}, headers=admin_headers
    )
    assert sale.status_code == 201
    before = _snapshot(clean_db)
    assert before["sales"] == 1
    assert before["stock"] == 3

    result = _run_script("backup.sh", backup_dir=tmp_path)
    dumps = list(tmp_path.glob("*.dump"))
    assert len(dumps) == 1, result.stdout

    # Намеренное повреждение: удаляем продажи и портим остаток.
    with clean_db.begin() as conn:
        conn.execute(text("DELETE FROM sales"))
        conn.execute(text("UPDATE discs SET stock = 999"))
    assert _snapshot(clean_db) != before

    _run_script("restore.sh", str(dumps[0]), backup_dir=tmp_path)

    assert _snapshot(clean_db) == before
