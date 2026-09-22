from financeiro_dr.database.connection import Database

def test_connection_enables_foreign_keys_and_wal(tmp_path):
    con=Database(tmp_path/"financeiro.db").connect()
    try:
        assert con.execute("PRAGMA foreign_keys").fetchone()[0]==1
        assert con.execute("PRAGMA journal_mode").fetchone()[0].lower()=="wal"
    finally: con.close()
