"""Read-only central API prototype. Bind to loopback; use a private authenticated tunnel.

Do not publish this server directly on the public internet.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
import threading
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
            self._tokens[token] = dict(user)
        return token

    def get(self, token: str) -> dict | None:
        with self._lock:
            value = self._tokens.get(token)
            return dict(value) if value else None


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
