import pytest
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.security.auth_service import AuthService, AuthenticationError


@pytest.fixture
def auth(tmp_path):
    con = Database(tmp_path / "recovery.db").connect()
    MigrationRunner().apply_all(con)
    try:
        yield AuthService(con)
    finally:
        con.close()


def test_recovery_code_is_hashed_and_rotated(auth):
    code = auth.initialize_password("Senha Antiga 123!")
    stored = auth.connection.execute(
        "SELECT token_hash FROM password_recovery WHERE id=1"
    ).fetchone()[0]
    assert code not in stored
    with pytest.raises(AuthenticationError):
        auth.reset_password("INVALIDA", "Nova Senha 456!")
    assert auth.authenticate("Senha Antiga 123!")
    next_code = auth.reset_password(code, "Nova Senha 456!")
    assert auth.authenticate("Nova Senha 456!")
    assert not auth.authenticate("Senha Antiga 123!")
    assert code != next_code
    with pytest.raises(AuthenticationError):
        auth.reset_password(code, "Terceira Senha 789!")


def test_existing_user_can_generate_recovery_code(auth):
    auth.initialize_password("Senha Atual 123!")
    auth.connection.execute("DELETE FROM password_recovery")
    auth.connection.commit()
    with pytest.raises(AuthenticationError):
        auth.regenerate_recovery_code("errada")
    code = auth.regenerate_recovery_code("Senha Atual 123!")
    assert auth.reset_password(code, "Senha Nova 123!")
    assert auth.authenticate("Senha Nova 123!")


def test_weak_password_cannot_consume_recovery_code(auth):
    code = auth.initialize_password("Senha Atual 123!")
    with pytest.raises(ValueError):
        auth.reset_password(code, "curta")
    assert auth.reset_password(code, "Senha Nova 123!")
