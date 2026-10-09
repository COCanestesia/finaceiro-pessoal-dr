import csv
import sqlite3
import pytest
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.database.backup import create_backup, export_entries_csv


def test_backup_is_consistent_and_preserves_auth(tmp_path):
    con = Database(tmp_path / "source.db").connect()
    MigrationRunner().apply_all(con)
    con.execute("INSERT INTO local_user(id, password_hash) VALUES(1,'test-hash')")
    con.execute("INSERT INTO financial_entry(competence_date,description,amount_cents,entry_type,status) VALUES ('2026-10-09','Consulta',15025,'RECEITA','RECEBIDO')")
    destination = tmp_path / "backup.db"
    try:
        create_backup(con, destination)
        restored = sqlite3.connect(destination)
        try:
            assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert restored.execute("SELECT password_hash FROM local_user").fetchone()[0] == "test-hash"
            assert restored.execute("SELECT amount_cents FROM financial_entry").fetchone()[0] == 15025
        finally:
            restored.close()
        with pytest.raises(FileExistsError):
            create_backup(con, destination)
        exported = export_entries_csv(con, tmp_path / "lancamentos.csv")
        with exported.open(encoding="utf-8-sig", newline="") as infile:
            rows = list(csv.DictReader(infile, delimiter=";"))
        assert len(rows) == 1
        assert rows[0]["amount_cents"] == "15025"
    finally:
        con.close()
