import json
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.security.access_service import AccessService
from financeiro_dr.network.read_api import create_server


def test_remote_post_permissions_and_audit(tmp_path):
    db = tmp_path / "shared.db"
    con = Database(db).connect()
    MigrationRunner().apply_all(con)
    users = AccessService(con)
    users.create_user("leitor", "Leitor", "Senha Forte 123!", "consulta")
    users.create_user("financeiro", "Financeiro", "Senha Forte 123!", "financeiro")
    con.commit()
    con.close()
    server = create_server(db, port=0)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{server.server_port}"
    def post(path, data, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = Request(base + path, data=json.dumps(data).encode(), headers=headers)
        with urlopen(req) as res:
            return res.status, json.load(res)
    record = {"competence_date":"2026-10-09","description":"Consulta teste",
              "amount_cents":12500,"entry_type":"RECEITA","status":"RECEBIDO"}
    try:
        _, reader = post("/v1/session", {"username":"leitor","password":"Senha Forte 123!"})
        _, writer = post("/v1/session", {"username":"financeiro","password":"Senha Forte 123!"})
        try:
            post("/v1/entries",record,reader["token"])
            assert False, "Leitor não deve gravar"
        except HTTPError as exc:
            assert exc.code == 403
        status, response = post("/v1/entries",record,writer["token"])
        assert status == 201 and response["id"] > 0
        with Database(db).connect() as check:
            assert check.execute("SELECT count(*) FROM financial_entry").fetchone()[0] == 1
            assert check.execute("SELECT count(*) FROM audit_log WHERE action='CREATE'").fetchone()[0] == 1
    finally:
        server.shutdown()
        server.server_close()
        t.join(timeout=3)
