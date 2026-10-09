from __future__ import annotations

import csv
from pathlib import Path
import sqlite3


def create_backup(connection: sqlite3.Connection, destination: Path) -> Path:
    """Consistent online SQLite backup, including records still stored in WAL."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError("O arquivo de backup já existe. Escolha outro nome.")
    backup = sqlite3.connect(destination)
    try:
        connection.backup(backup)
        result = backup.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError("O banco de backup não passou na verificação de integridade.")
    except BaseException:
        backup.close()
        destination.unlink(missing_ok=True)
        raise
    else:
        backup.close()
    return destination


def export_entries_csv(connection: sqlite3.Connection, destination: Path) -> Path:
    """Export live entries without using floating-point money."""
    columns = (
        "id", "competence_date", "due_date", "settled_date", "description",
        "amount_cents", "entry_type", "status", "payment_method", "notes",
    )
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = connection.execute(
        f"SELECT {', '.join(columns)} FROM financial_entry "
        "WHERE deleted_at IS NULL ORDER BY competence_date, id"
    )
    with destination.open("x", encoding="utf-8-sig", newline="") as output:
        writer = csv.writer(output, delimiter=";")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([row[column] if row[column] is not None else "" for column in columns])
    return destination
