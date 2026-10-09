import sqlite3
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.database.backup import create_backup
from financeiro_dr.database.restore import validate_backup, restore_backup_offline
import pytest


def test_restoration_preserves_original_and_restores_values(tmp_path):
    path = tmp_path / "active.db"
    con = Database(path).connect()
    MigrationRunner().apply_all(con)
    con.execute("INSERT INTO financial_entry(competence_date,description,amount_cents,entry_type,status) VALUES('2026-10-09','Original',200,'DESPESA','PAGO')")
    snapshot = create_backup(con, tmp_path / "saved.db")
    con.execute("UPDATE financial_entry SET amount_cents=999")
    con.close()
    restored = restore_backup_offline(snapshot, path)
    validate_backup(restored)
    with sqlite3.connect(restored) as check:
        assert check.execute("SELECT amount_cents FROM financial_entry").fetchone()[0] == 200
    safety = list(tmp_path.glob("active-antes-restauracao-*.db"))
    assert len(safety) == 1
    with sqlite3.connect(safety[0]) as check:
        assert check.execute("SELECT amount_cents FROM financial_entry").fetchone()[0] == 999


def test_restore_rejects_unrelated_file(tmp_path):
    unrelated = tmp_path / "unrelated.db"
    with sqlite3.connect(unrelated) as con:
        con.execute("CREATE TABLE unrelated(id integer)")
    with pytest.raises(ValueError):
        restore_backup_offline(unrelated, tmp_path / "active.db")
    assert not (tmp_path / "active.db").exists()
