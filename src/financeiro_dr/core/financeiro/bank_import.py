from __future__ import annotations

import csv
import hashlib
import sqlite3
from pathlib import Path


def import_bank_csv(connection: sqlite3.Connection, account_id: int, path: Path) -> dict:
    """Import CSV bank lines to staging only; never create financial entries automatically.

    Expected columns: date, description, amount_cents. Signed cents: positive incoming,
    negative outgoing. Duplicates in the same account are skipped using stable hashes.
    """
    if connection.execute("SELECT 1 FROM bank_account WHERE id=? AND active=1", (account_id,)).fetchone() is None:
        raise ValueError("Conta bancária inválida.")
    added = skipped = 0
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not {"date", "description", "amount_cents"} <= set(reader.fieldnames):
            raise ValueError("CSV precisa das colunas date, description e amount_cents.")
        rows = list(reader)
    prepared = []
    from datetime import date
    for row in rows:
        day = date.fromisoformat(row["date"].strip()).isoformat()
        description = row["description"].strip()
        amount = int(row["amount_cents"].strip())
        if not description or amount == 0:
            raise ValueError("Descrição vazia ou valor zero.")
        fingerprint = hashlib.sha256(f"{account_id}|{day}|{description}|{amount}".encode()).hexdigest()
        prepared.append((account_id, day, description, amount, fingerprint))
    connection.execute("SAVEPOINT import_csv")
    try:
        for values in prepared:
            cur = connection.execute(
                "INSERT OR IGNORE INTO bank_statement_line(account_id,posted_date,description,amount_cents,fingerprint) VALUES(?,?,?,?,?)",
                values,
            )
            if cur.rowcount:
                added += 1
            else:
                skipped += 1
        connection.execute("RELEASE SAVEPOINT import_csv")
    except Exception:
        connection.execute("ROLLBACK TO SAVEPOINT import_csv")
        connection.execute("RELEASE SAVEPOINT import_csv")
        raise
    return {"imported": added, "duplicates": skipped}
