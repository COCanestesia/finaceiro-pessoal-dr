from __future__ import annotations

import sqlite3
import secrets

from financeiro_dr.security.passwords import hash_password, verify_password


class AuthenticationError(RuntimeError):
    """Authentication rule violation safe to show to the local user."""


class AuthService:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def has_password(self) -> bool:
        row = self.connection.execute("SELECT 1 FROM local_user WHERE id = 1").fetchone()
        return row is not None

    def initialize_password(self, password: str) -> str:
        password_hash = hash_password(password)
        recovery_code = secrets.token_hex(16).upper()
        recovery_hash = hash_password(recovery_code)
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            existing = self.connection.execute("SELECT 1 FROM local_user WHERE id = 1").fetchone()
            if existing is not None:
                raise AuthenticationError("A senha local já foi definida.")
            self.connection.execute("INSERT INTO local_user(id, password_hash) VALUES (1, ?)", (password_hash,))
            self.connection.execute("INSERT INTO password_recovery(id, token_hash) VALUES (1, ?)", (recovery_hash,))
            self.connection.commit()
            return recovery_code
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

    def reset_password(self, recovery_code: str, new_password: str) -> str:
        """Reset with the offline recovery code; rotate code after successful use."""
        new_hash = hash_password(new_password)
        next_code = secrets.token_hex(16).upper()
        next_code_hash = hash_password(next_code)
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute("SELECT token_hash FROM password_recovery WHERE id = 1").fetchone()
            if row is None or not verify_password(row[0], recovery_code.strip().replace("-", "").upper()):
                raise AuthenticationError("Chave de recuperação incorreta ou indisponível.")
            self.connection.execute("UPDATE local_user SET password_hash = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = 1", (new_hash,))
            self.connection.execute("UPDATE password_recovery SET token_hash = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = 1", (next_code_hash,))
            self.connection.commit()
            return next_code
        except Exception:
            if self.connection.in_transaction:
                self.connection.rollback()
            raise

    def regenerate_recovery_code(self, password: str) -> str:
        """For existing installs: generate a code after authenticating normally."""
        if not self.authenticate(password):
            raise AuthenticationError("Senha atual incorreta.")
        code = secrets.token_hex(16).upper()
        code_hash = hash_password(code)
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self.connection.execute("INSERT INTO password_recovery(id, token_hash) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET token_hash=excluded.token_hash, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')", (code_hash,))
            self.connection.commit()
            return code
        except Exception:
            if self.connection.in_transaction:
                self.connection.rollback()
            raise
