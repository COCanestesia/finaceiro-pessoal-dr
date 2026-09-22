from __future__ import annotations

import sqlite3

from financeiro_dr.security.passwords import hash_password, verify_password


class AuthenticationError(RuntimeError):
    """Authentication rule violation safe to show to the local user."""


class AuthService:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def has_password(self) -> bool:
        row = self.connection.execute("SELECT 1 FROM local_user WHERE id = 1").fetchone()
        return row is not None

    def initialize_password(self, password: str) -> None:
        password_hash = hash_password(password)
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            existing = self.connection.execute("SELECT 1 FROM local_user WHERE id = 1").fetchone()
            if existing is not None:
                raise AuthenticationError("A senha local já foi definida.")
            self.connection.execute("INSERT INTO local_user(id, password_hash) VALUES (1, ?)", (password_hash,))
            self.connection.commit()
        except Exception:
            if self.connection.in_transaction:
                self.connection.rollback()
            raise

    def authenticate(self, password: str) -> bool:
        row = self.connection.execute("SELECT password_hash FROM local_user WHERE id = 1").fetchone()
        if row is None:
            return False
        return verify_password(row[0], password)

    def change_password(self, current: str, new: str) -> None:
        new_hash = hash_password(new)
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute("SELECT password_hash FROM local_user WHERE id = 1").fetchone()
            if row is None or not verify_password(row[0], current):
                raise AuthenticationError("Senha atual incorreta.")
            self.connection.execute("UPDATE local_user SET password_hash = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = 1", (new_hash,))
            self.connection.commit()
        except Exception:
            if self.connection.in_transaction:
                self.connection.rollback()
            raise
