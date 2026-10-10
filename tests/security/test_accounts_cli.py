import pytest
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.network.accounts_cli import add_account, list_accounts


def test_account_creation_and_listing(tmp_path):
    con = Database(tmp_path / "accounts.db").connect()
    MigrationRunner().apply_all(con)
    try:
        with pytest.raises(ValueError):
            add_account(con, "admin", "Admin", "admin", "short")
        user_id = add_account(con, "administrador", "Administrador", "admin", "Senha Segura 123!")
        users = list_accounts(con)
        assert users == [{"id": user_id, "username": "administrador",
                          "display_name": "Administrador", "role": "admin", "active": 1}]
        assert "password_hash" not in str(users)
    finally:
        con.close()
