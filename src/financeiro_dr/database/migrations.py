from __future__ import annotations

from pathlib import Path
import sqlite3


class MigrationError(RuntimeError):
    pass


class MigrationRunner:
    def __init__(self, migrations_dir: Path | None = None):
        self.migrations_dir = migrations_dir or (Path(__file__).with_name("migrations"))

    def apply_all(self, connection: sqlite3.Connection) -> None:
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    name TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                )
                """
            )
            applied = {row[0] for row in connection.execute("SELECT name FROM schema_migrations")}
            for path in sorted(self.migrations_dir.glob("*.sql")):
                if path.name in applied:
                    continue
                sql = path.read_text(encoding="utf-8")
                migration_name = path.name.replace("'", "''")
                script = "BEGIN IMMEDIATE;\n" + sql + "\nINSERT INTO schema_migrations(name) VALUES ('" + migration_name + "');\nCOMMIT;"
                try:
                    connection.executescript(script)
                except sqlite3.Error:
                    if connection.in_transaction:
                        connection.rollback()
                    raise
        except (sqlite3.Error, OSError) as exc:
            raise MigrationError("Não foi possível atualizar a estrutura do banco de dados.") from exc
