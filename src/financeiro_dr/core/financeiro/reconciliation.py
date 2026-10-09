from __future__ import annotations

import sqlite3
from datetime import date


def suggested_matches(connection: sqlite3.Connection, statement_id: int, tolerance_days: int = 3) -> list[dict]:
    """Suggest entries; do not match automatically or change money."""
    line = connection.execute(
        "SELECT id,account_id,posted_date,amount_cents,matched_entry_id "
        "FROM bank_statement_line WHERE id=?", (statement_id,)
    ).fetchone()
    if line is None:
        raise ValueError("Movimentação bancária não encontrada.")
    if line["matched_entry_id"] is not None:
        return []
    sign_type = "RECEITA" if line["amount_cents"] > 0 else "DESPESA"
    amount = abs(line["amount_cents"])
    rows = connection.execute(
        "SELECT id,description,amount_cents,due_date,settled_date,competence_date "
        "FROM financial_entry WHERE deleted_at IS NULL AND status <> 'CANCELADO' "
        "AND entry_type=? AND amount_cents=? "
        "AND (bank_account_id=? OR bank_account_id IS NULL) "
        "AND id NOT IN (SELECT matched_entry_id FROM bank_statement_line WHERE matched_entry_id IS NOT NULL)",
        (sign_type, amount, line["account_id"]),
    ).fetchall()
    posted = date.fromisoformat(line["posted_date"])
    suggestions = []
    for row in rows:
        dates = [date.fromisoformat(row[key]) for key in ("settled_date", "due_date", "competence_date") if row[key]]
        if not dates:
            continue
        days = min(abs((posted - day).days) for day in dates)
        if days <= tolerance_days:
            suggestions.append({
                "entry_id": row["id"], "description": row["description"],
                "amount_cents": row["amount_cents"], "days_apart": days,
            })
    return sorted(suggestions, key=lambda candidate: (candidate["days_apart"], candidate["entry_id"]))


def confirm_match(connection: sqlite3.Connection, statement_id: int, entry_id: int) -> None:
    """Confirm an operator-selected match, rejecting incompatible suggestions."""
    candidates = suggested_matches(connection, statement_id)
    if entry_id not in {row["entry_id"] for row in candidates}:
        raise ValueError("O lançamento não corresponde à movimentação bancária.")
    cursor = connection.execute(
        "UPDATE bank_statement_line SET matched_entry_id=? WHERE id=? AND matched_entry_id IS NULL",
        (entry_id, statement_id),
    )
    if cursor.rowcount != 1:
        raise ValueError("Movimentação já conciliada.")
