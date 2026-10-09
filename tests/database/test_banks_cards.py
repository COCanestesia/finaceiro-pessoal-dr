from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner


def test_bank_and_card_registration_and_links(tmp_path):
    con = Database(tmp_path / "bank.db").connect()
    try:
        MigrationRunner().apply_all(con)
        assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        bank = con.execute("INSERT INTO bank_account(name,institution) VALUES (?,?)", ("Conta Principal", "Banco")).lastrowid
        card = con.execute("INSERT INTO credit_card(name,bank_account_id,closing_day,due_day) VALUES (?,?,?,?)", ("Cartão Pessoal", bank, 5, 15)).lastrowid
        con.execute(
            "INSERT INTO financial_entry(competence_date,description,amount_cents,entry_type,status,bank_account_id,card_id)"
            " VALUES ('2026-10-09','Compra',2500,'DESPESA','PAGO',?,?)",
            (bank, card),
        )
        row = con.execute("SELECT bank_account_id,card_id FROM financial_entry").fetchone()
        assert (row[0], row[1]) == (bank, card)
        MigrationRunner().apply_all(con)
        assert con.execute("SELECT COUNT(*) FROM bank_account").fetchone()[0] == 1
    finally:
        con.close()
