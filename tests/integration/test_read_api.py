import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from threading import Thread

import pytest
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.security.access_service import AccessService
from financeiro_dr.network.read_api import create_server, SessionStore


def test_session_expiration(monkeypatch):
    import financeiro_dr.network.read_api as api
    now = [1000.0]
    monkeypatch.setattr(api.time, "monotonic", lambda: now[0])
    store = SessionStore()
    token = store.issue({"id": 1, "role": "consulta"})
    assert store.get(token)["id"] == 1
    now[0] += 3601
    assert store.get(token) is None


def test_private_read_api_authentication(tmp_path):
    db = tmp_path / "test.db"
    con = Database(db).connect()
    MigrationRunner().apply_all(con)
    access = AccessService(con)
    access.create_user("drconsulta", "Dr", "Senha Forte 123!", "consulta")
    con.execute(
        "INSERT INTO financial_entry(competence_date,description,amount_cents,entry_type,status)"
        " VALUES ('2026-10-09','Teste',1000,'DESPESA','PAGO')"
    )
    con.close()
    with pytest.raises(ValueError):
        create_server(db, host="0.0.0.0")
    server = create_server(db, port=0)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = "http://127.0.0.1:" + str(server.server_port)
    try:
        with pytest.raises(HTTPError) as exc:
            urlopen(url + "/v1/entries")
        assert exc.value.code == 401
        payload = json.dumps({"username": "drconsulta", "password": "Senha Forte 123!"}).encode()
        request = Request(url + "/v1/session", data=payload, headers={"Content-Type": "application/json"})
        with urlopen(request) as res:
            token = json.load(res)["token"]
        request = Request(url + "/v1/entries", headers={"Authorization": "Bearer " + token})
        with urlopen(request) as res:
            assert json.load(res)["entries"][0]["amount_cents"] == 1000
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
