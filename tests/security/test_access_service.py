import pytest
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.security.access_service import AccessService, AccessDenied


@pytest.fixture
def access(tmp_path):
    con = Database(tmp_path / "roles.db").connect()
    MigrationRunner().apply_all(con)
    try:
        yield AccessService(con)
    finally:
        con.close()


def test_individual_login_and_case_insensitive_username(access):
    access.create_user("financeiro", "Financeiro", "Senha Forte 123!", "financeiro")
    assert access.authenticate("FINANCEIRO", "Senha Forte 123!")["role"] == "financeiro"
    assert access.authenticate("financeiro", "incorreta") is None
    stored = access.connection.execute("SELECT password_hash FROM access_user").fetchone()[0]
    assert "Senha Forte 123!" not in stored


def test_reader_cannot_write_and_finance_cannot_manage_users(access):
    access.create_user("consulta", "Consulta", "Senha Forte 123!", "consulta")
    access.create_user("financeiro", "Financeiro", "Senha Forte 123!", "financeiro")
    reader = access.authenticate("consulta", "Senha Forte 123!")
    worker = access.authenticate("financeiro", "Senha Forte 123!")
    access.require_permission(reader, "read")
    with pytest.raises(AccessDenied):
        access.require_permission(reader, "write")
    access.require_permission(worker, "write")
    with pytest.raises(AccessDenied):
        access.require_permission(worker, "users")


def test_deactivated_user_cannot_login(access):
    admin_id = access.create_user("administrador", "Administrador", "Senha Forte 123!", "admin")
    worker_id = access.create_user("financeiro", "Financeiro", "Senha Forte 123!", "financeiro")
    admin = access.authenticate("administrador", "Senha Forte 123!")
    with pytest.raises(AccessDenied):
        access.deactivate_user(admin, admin_id)
    access.deactivate_user(admin, worker_id)
    assert access.authenticate("financeiro", "Senha Forte 123!") is None
