from __future__ import annotations

import sqlite3
from financeiro_dr.security.passwords import hash_password, verify_password


class AccessDenied(PermissionError):
    pass


ROLE_PERMISSIONS = {
    "admin": frozenset({"read", "write", "users", "backup"}),
    "financeiro": frozenset({"read", "write"}),
    "consulta": frozenset({"read"}),
}


class AccessService:
    """Server-side identities: deliberately separate from legacy offline login."""

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create_user(self, username: str, display_name: str, password: str, role: str) -> int:
        username = username.strip()
        display_name = display_name.strip()
        if len(username) < 3 or not display_name:
            raise ValueError("Informe usuário (mínimo 3 caracteres) e nome.")
        if role not in ROLE_PERMISSIONS:
            raise ValueError("Perfil inválido.")
        hashed = hash_password(password)
        cursor = self.connection.execute(
            "INSERT INTO access_user(username,display_name,password_hash,role) VALUES(?,?,?,?)",
            (username, display_name, hashed, role),
        )
        return int(cursor.lastrowid)

    def authenticate(self, username: str, password: str) -> dict | None:
        row = self.connection.execute(
            "SELECT id,username,display_name,password_hash,role,active "
            "FROM access_user WHERE username=? COLLATE NOCASE",
            (username.strip(),),
        ).fetchone()
        if row is None or not verify_password(row["password_hash"], password):
            return None
        if not row["active"]:
            return None
        return {key: row[key] for key in ("id", "username", "display_name", "role")}

    @staticmethod
    def require_permission(user: dict | None, permission: str) -> None:
        if user is None or permission not in ROLE_PERMISSIONS.get(user.get("role"), frozenset()):
            raise AccessDenied("Usuário sem permissão para esta operação.")

    def deactivate_user(self, actor: dict, user_id: int) -> None:
        self.require_permission(actor, "users")
        if actor["id"] == user_id:
            raise AccessDenied("Não é permitido desativar a própria conta.")
        self.connection.execute(
            "UPDATE access_user SET active=0 WHERE id=?", (user_id,)
        )
