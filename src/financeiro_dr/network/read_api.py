"""Read-only central API prototype. Bind to loopback; use a private authenticated tunnel.

Do not publish this server directly on the public internet.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from financeiro_dr.security.access_service import AccessService


class SessionStore:
    def __init__(self):
        self._tokens: dict[str, dict] = {}
        self._lock = threading.Lock()

    def issue(self, user: dict) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._tokens[token] = (dict(user), time.monotonic() + 3600)
        return token

    def get(self, token: str) -> dict | None:
        with self._lock:
            value = self._tokens.get(token)
            if not value:
                return None
            user, expires_at = value
            if time.monotonic() >= expires_at:
                self._tokens.pop(token, None)
                return None
            return dict(user)


def make_handler(db_path: Path, sessions: SessionStore):
    db_path = Path(db_path)

    class Handler(BaseHTTPRequestHandler):
        def _respond(self, status: int, value: dict):
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _connection(self):
            # A connection per request avoids SQLite cross-thread connection sharing.
            con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True, timeout=10)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA query_only=ON")
            return con

        def do_POST(self):
            if urlsplit(self.path).path == "/v1/entries":
                self._create_entry()
                return
            if urlsplit(self.path).path != "/v1/session":
                self._respond(404, {"error": "Não encontrado"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 4096:
                    self._respond(400, {"error": "Requisição inválida"})
                    return
                payload = json.loads(self.rfile.read(length))
                username, password = payload["username"], payload["password"]
                if not isinstance(username, str) or not isinstance(password, str):
                    raise ValueError
                with self._connection() as con:
                    user = AccessService(con).authenticate(username, password)
                if not user:
                    self._respond(401, {"error": "Credenciais inválidas"})
                    return
                self._respond(200, {"token": sessions.issue(user), "user": user})
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                self._respond(400, {"error": "Requisição inválida"})

        def _create_entry(self):
            header = self.headers.get("Authorization", "")
            token = header[7:] if header.startswith("Bearer ") else ""
            identity = sessions.get(token)
            if not identity:
                self._respond(401, {"error": "Autenticação necessária"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4096:
                    raise ValueError
                payload = json.loads(self.rfile.read(length))
                from datetime import date
                day = date.fromisoformat(payload["competence_date"]).isoformat()
                name = payload["description"].strip()
                amount = payload["amount_cents"]
                kind = payload["entry_type"]
                status = payload["status"]
                if not isinstance(name, str) or not 1 <= len(name) <= 300:
                    raise ValueError
                if type(amount) is not int or amount < 0 or amount > 10**12:
                    raise ValueError
                if kind not in ("RECEITA", "DESPESA") or status not in ("PENDENTE", "PAGO", "RECEBIDO"):
                    raise ValueError
                if (kind == "RECEITA" and status == "PAGO") or (kind == "DESPESA" and status == "RECEBIDO"):
                    raise ValueError
            except (ValueError, TypeError, KeyError, AttributeError, json.JSONDecodeError):
                self._respond(400, {"error": "Lançamento inválido"})
                return
            con = sqlite3.connect(str(db_path), timeout=15)
            con.row_factory = sqlite3.Row
            try:
                con.execute("PRAGMA busy_timeout=15000")
                con.execute("BEGIN IMMEDIATE")
                current = con.execute("SELECT role,active FROM access_user WHERE id=?", (identity["id"],)).fetchone()
                if not current or not current["active"] or current["role"] not in ("admin", "financeiro"):
                    con.rollback()
                    self._respond(403, {"error": "Sem permissão para gravar"})
                    return
                cursor = con.execute(
                    "INSERT INTO financial_entry(competence_date,description,amount_cents,entry_type,status) VALUES(?,?,?,?,?)",
                    (day,name,amount,kind,status),
                )
                entry_id = cursor.lastrowid
                con.execute(
                    "INSERT INTO audit_log(entity,entity_id,action,snapshot_json) VALUES(?,?,?,?)",
                    ("financial_entry",entry_id,"CREATE",json.dumps({"source":"remote_api","actor_id":identity["id"],"description":name,"amount_cents":amount})),
                )
                con.commit()
                self._respond(201, {"id": entry_id})
            except sqlite3.Error:
                con.rollback()
                self._respond(503, {"error": "Falha ao registrar lançamento"})
            finally:
                con.close()

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/v1/health":
                self._respond(200, {"status": "ok"})
                return
            if path != "/v1/entries":
                self._respond(404, {"error": "Não encontrado"})
                return
            header = self.headers.get("Authorization", "")
            token = header[7:] if header.startswith("Bearer ") else ""
            user = sessions.get(token)
            if not user:
                self._respond(401, {"error": "Autenticação necessária"})
                return
            with self._connection() as con:
                current = con.execute(
                    "SELECT role, active FROM access_user WHERE id=?", (user["id"],)
                ).fetchone()
                if not current or not current["active"]:
                    self._respond(403, {"error": "Acesso revogado"})
                    return
                AccessService.require_permission({"role": current["role"]}, "read")
                rows = con.execute(
                    "SELECT id, competence_date, description, amount_cents, entry_type, status "
                    "FROM financial_entry WHERE deleted_at IS NULL "
                    "ORDER BY competence_date DESC, id DESC LIMIT 100"
                ).fetchall()
            self._respond(200, {"entries": [dict(row) for row in rows]})

        def log_message(self, format, *args):
            # Never log credentials, session tokens or private financial data.
            pass

    return Handler


def create_server(db_path: Path, host: str = "127.0.0.1", port: int = 8765):
    if host not in ("127.0.0.1", "localhost"):
        raise ValueError("Este protótipo deve usar somente loopback e túnel privado.")
    return ThreadingHTTPServer((host, port), make_handler(db_path, SessionStore()))


def main(argv=None) -> int:
    """Start local-only API for a private HTTPS reverse proxy."""
    import argparse
    from financeiro_dr.app_paths import AppPaths
    parser = argparse.ArgumentParser(description="Servidor privado Financeiro Pessoal DR")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    server = create_server(AppPaths.from_environment().database_file, port=args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
