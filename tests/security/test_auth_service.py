import pytest
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.security.auth_service import AuthService,AuthenticationError

@pytest.fixture
def connection(tmp_path):
    con=Database(tmp_path/"auth.db").connect(); MigrationRunner().apply_all(con)
    try: yield con
    finally: con.close()
@pytest.fixture
def auth_service(connection): return AuthService(connection)

def test_password_is_never_stored_in_plain_text(auth_service,connection):
    auth_service.initialize_password("Senha Forte 123!"); stored=connection.execute("select password_hash from local_user where id=1").fetchone()[0]; assert stored!="Senha Forte 123!"; assert stored.startswith("$argon2"); assert auth_service.authenticate("Senha Forte 123!") is True; assert auth_service.authenticate("errada") is False

def test_initialize_password_only_once(auth_service):
    auth_service.initialize_password("Senha Forte 123!")
    with pytest.raises(AuthenticationError,match="já foi definida"): auth_service.initialize_password("Outra Senha 123!")

def test_change_password_requires_current_password(auth_service):
    auth_service.initialize_password("Senha Forte 123!")
    with pytest.raises(AuthenticationError,match="Senha atual incorreta"): auth_service.change_password("errada","Nova Senha 456!")
    assert auth_service.authenticate("Senha Forte 123!") is True

def test_change_password_replaces_hash(auth_service):
    auth_service.initialize_password("Senha Forte 123!"); auth_service.change_password("Senha Forte 123!","Nova Senha 456!"); assert auth_service.authenticate("Senha Forte 123!") is False; assert auth_service.authenticate("Nova Senha 456!") is True

def test_password_requires_at_least_eight_characters(auth_service):
    with pytest.raises(ValueError,match="pelo menos 8 caracteres"): auth_service.initialize_password("curta")

def test_has_password_reports_first_use(auth_service):
    assert auth_service.has_password() is False; auth_service.initialize_password("Senha Forte 123!"); assert auth_service.has_password() is True
