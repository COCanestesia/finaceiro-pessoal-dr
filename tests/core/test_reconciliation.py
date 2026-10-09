from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.core.financeiro.reconciliation import suggested_matches, confirm_match
import pytest


def test_matching_requires_correct_sign_amount_and_date(tmp_path):
    con = Database(tmp_path / "data.db").connect()
    MigrationRunner().apply_all(con)
    bank = con.execute("INSERT INTO bank_account(name) VALUES('Conta')").lastrowid
    entry = con.execute(
        "INSERT INTO financial_entry(competence_date,due_date,description,amount_cents,entry_type,status,bank_account_id)"
        " VALUES('2026-10-09','2026-10-09','Despesa',1250,'DESPESA','PAGO',?)", (bank,)
    ).lastrowid
    line = con.execute(
        "INSERT INTO bank_statement_line(account_id,posted_date,description,amount_cents,fingerprint)"
        " VALUES(?,'2026-10-09','Pagamento',-1250,'fingerprint')", (bank,)
    ).lastrowid
    try:
        assert suggested_matches(con, line)[0]["entry_id"] == entry
        confirm_match(con, line, entry)
        assert suggested_matches(con, line) == []
        with pytest.raises(ValueError):
            confirm_match(con, line, entry)
    finally:
        con.close()
