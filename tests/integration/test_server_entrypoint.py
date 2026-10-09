from financeiro_dr.network.read_api import main
from financeiro_dr.network.bootstrap_admin import main as bootstrap_main
from financeiro_dr.network.read_api import create_server
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner


def test_server_entrypoint_and_bootstrap_available(tmp_path):
    db = tmp_path / "server.db"
    connection = Database(db).connect()
    MigrationRunner().apply_all(connection)
    connection.close()
    server = create_server(db, port=0)
    try:
        assert server.server_address[0] == "127.0.0.1"
        assert callable(main)
        assert callable(bootstrap_main)
    finally:
        server.server_close()
