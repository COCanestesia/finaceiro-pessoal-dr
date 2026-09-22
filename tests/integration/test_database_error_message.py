import sqlite3

def test_locked_database_has_user_safe_message():
    from financeiro_dr.ui.error_handler import database_error_message
    message=database_error_message(sqlite3.OperationalError("database is locked")); assert message=="O banco de dados está ocupado. Tente novamente em alguns segundos."; assert "Traceback" not in message

def test_other_database_error_is_generic():
    from financeiro_dr.ui.error_handler import database_error_message
    assert database_error_message(sqlite3.DatabaseError("file is not a database"))=="Não foi possível concluir a operação no banco de dados local."
