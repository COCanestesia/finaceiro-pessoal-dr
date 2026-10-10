import pytest
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.network.accounts_cli import main
from financeiro_dr.security.access_service import AccessService


def test_additional_user_requires_admin_password(tmp_path, monkeypatch):
    import financeiro_dr.network.accounts_cli as cli
    path = tmp_path / "users.db"
    con = Database(path).connect()
    MigrationRunner().apply_all(con)
    AccessService(con).create_user("adminprincipal", "Administrador", "Senha de teste 123!", "admin")
    con.commit()
    con.close()
    monkeypatch.setattr(cli.AppPaths, "from_environment", lambda: type("P", (), {"database_file": path})())
    answers = iter(["funcionario", "Financeiro", "financeiro", "adminprincipal"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    secret = iter(["Nova senha 123!", "Nova senha 123!", "Senha de teste 123!"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": next(secret))
    assert main(["add"]) == 0
    with Database(path).connect() as check:
        assert check.execute("SELECT role FROM access_user WHERE username='funcionario'").fetchone()[0] == "financeiro"


def test_additional_user_denied_with_bad_admin_password(tmp_path, monkeypatch):
    import financeiro_dr.network.accounts_cli as cli
    path = tmp_path / "users.db"
    con = Database(path).connect()
    MigrationRunner().apply_all(con)
    AccessService(con).create_user("adminprincipal", "Administrador", "Senha de teste 123!", "admin")
    con.commit()
    con.close()
    monkeypatch.setattr(cli.AppPaths, "from_environment", lambda: type("P", (), {"database_file": path})())
    answers = iter(["funcionario", "Financeiro", "financeiro", "adminprincipal"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    secret = iter(["Nova senha 123!", "Nova senha 123!", "senha incorreta"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": next(secret))
    with pytest.raises(PermissionError):
        main(["add"])
    with Database(path).connect() as check:
        assert check.execute("SELECT COUNT(*) FROM access_user").fetchone()[0] == 1
