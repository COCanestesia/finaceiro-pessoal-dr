from __future__ import annotations

from pathlib import Path
import sqlite3


class DatabaseError(RuntimeError):
    """User-safe database failure."""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(self.path, timeout=10, isolation_level=None)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA foreign_keys=ON")
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=FULL")
            return con
        except sqlite3.Error as exc:
            raise DatabaseError("Não foi possível abrir o banco de dados local.") from exc
