from __future__ import annotations

from pathlib import Path
import sqlite3


def validate_backup(path: Path) -> None:
    path = Path(path)
    if not path.is_file() or path.stat().st_size < 100:
        raise ValueError("Arquivo de backup inválido.")
    uri = path.resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Backup corrompido.")
        required = {"financial_entry", "local_user", "schema_migrations"}
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required <= tables:
            raise ValueError("O arquivo não é um backup compatível do Financeiro DR.")
    finally:
        con.close()


def restore_backup_offline(source: Path, destination: Path) -> Path:
    """Only call while the app and all DB connections are closed.

    Preserve a full pre-restore snapshot; restore into a temporary DB first.
    """
    from datetime import datetime
    import os
    source, destination = Path(source).resolve(), Path(destination).resolve()
    validate_backup(source)
    if source == destination:
        raise ValueError("Selecione um backup diferente do banco ativo.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        safety = destination.with_name(destination.stem + "-antes-restauracao-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".db")
        active = sqlite3.connect(destination)
        try:
            from financeiro_dr.database.backup import create_backup
            create_backup(active, safety)
        finally:
            active.close()
    temp = destination.with_name(destination.name + ".restoring")
    if temp.exists():
        raise FileExistsError("Já existe uma restauração temporária pendente.")
    try:
        from financeiro_dr.database.backup import create_backup
        with sqlite3.connect(source) as source_db:
            create_backup(source_db, temp)
        validate_backup(temp)
        os.replace(temp, destination)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    return destination
