import csv
import pytest
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.core.financeiro.bank_import import import_bank_csv


def test_statement_import_deduplicates_and_never_posts_entries(tmp_path):
    con = Database(tmp_path / "test.db").connect()
    MigrationRunner().apply_all(con)
    account = con.execute("INSERT INTO bank_account(name) VALUES('Principal')").lastrowid
    file = tmp_path / "statement.csv"
    with file.open("w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(["date","description","amount_cents"])
        writer.writerow(["2026-10-09","Pagamento", -12500])
        writer.writerow(["2026-10-09","Pagamento", -12500])
    try:
        result = import_bank_csv(con, account, file)
        assert result == {"imported": 1, "duplicates": 1}
        assert import_bank_csv(con, account, file) == {"imported": 0, "duplicates": 2}
        assert con.execute("SELECT count(*) FROM financial_entry").fetchone()[0] == 0
    finally:
        con.close()


def test_invalid_import_is_atomic(tmp_path):
    con = Database(tmp_path / "test.db").connect()
    MigrationRunner().apply_all(con)
    account = con.execute("INSERT INTO bank_account(name) VALUES('Principal')").lastrowid
    path = tmp_path / "invalid.csv"
    path.write_text("date,description,amount_cents\n2026-10-09,OK,-1200\ninvalid-date,Erro,100\n", encoding="utf-8")
    try:
        with pytest.raises(ValueError):
            import_bank_csv(con, account, path)
        assert con.execute("SELECT count(*) FROM bank_statement_line").fetchone()[0] == 0
    finally:
        con.close()
