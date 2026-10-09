from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree


def _tag(block: str, name: str) -> str:
    m = re.search(r"<" + name + r">([^<\\r\\n]+)", block, re.I)
    return m.group(1).strip() if m else ""


def import_ofx(connection: sqlite3.Connection, account_id: int, path: Path) -> dict[str, int]:
    """Parse OFX 1.x SGML and OFX 2.x XML transactions into staging.

    FITID takes priority for deduplication; never posts actual ledger entries.
    """
    if not connection.execute("SELECT 1 FROM bank_account WHERE id=? AND active=1", (account_id,)).fetchone():
        raise ValueError("Conta inválida.")
    source = Path(path)
    if source.stat().st_size > 20_000_000:
        raise ValueError("Arquivo OFX muito grande.")
    raw = source.read_bytes()
    data = raw.decode("utf-8-sig", errors="replace")
    if "\ufffd" in data:
        data = raw.decode("cp1252", errors="replace")
    blocks = re.findall(r"<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>)|(?=</BANKTRANLIST>))", data, re.I | re.S)
    if not blocks:
        raise ValueError("Nenhuma movimentação STMTTRN encontrada.")
    prepared = []
    for block in blocks:
        day_raw = _tag(block, "DTPOSTED")
        amount_raw = _tag(block, "TRNAMT")
        desc = _tag(block, "MEMO") or _tag(block, "NAME") or "Movimentação"
        fitid = _tag(block, "FITID")
        if not day_raw or not amount_raw:
            raise ValueError("Movimentação OFX sem data ou valor.")
        try:
            day = datetime.strptime(day_raw[:8], "%Y%m%d").date().isoformat()
            from decimal import Decimal, ROUND_HALF_UP
            amount = int((Decimal(amount_raw.replace(",", ".")) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        except (ValueError, ArithmeticError) as exc:
            raise ValueError("Data ou valor OFX inválido.") from exc
        if amount == 0:
            raise ValueError("O extrato contém movimentação de valor zero.")
        fingerprint = hashlib.sha256(f"{account_id}|{fitid or day+'|'+desc+'|'+str(amount)}".encode()).hexdigest()
        prepared.append((account_id, day, desc, amount, fingerprint))
    added = skipped = 0
    connection.execute("SAVEPOINT ofx_import")
    try:
        for record in prepared:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO bank_statement_line(account_id,posted_date,description,amount_cents,fingerprint) VALUES(?,?,?,?,?)",
                record,
            )
            if cursor.rowcount:
                added += 1
            else:
                skipped += 1
        connection.execute("RELEASE SAVEPOINT ofx_import")
    except Exception:
        connection.execute("ROLLBACK TO SAVEPOINT ofx_import")
        connection.execute("RELEASE SAVEPOINT ofx_import")
        raise
    return {"imported": added, "duplicates": skipped}
