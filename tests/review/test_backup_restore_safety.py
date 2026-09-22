from pathlib import Path
import sqlite3
import zipfile

import pytest

from financeiro_dr.backup import BackupService, InvalidBackupError, RestoreService
from financeiro_dr.database.migrations import MigrationRunner


def open_db(path: Path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    MigrationRunner().apply_all(connection)
    return connection


def test_invalid_restore_does_not_change_current_database(tmp_path):
    db_path = tmp_path / "financeiro.db"
    connection = open_db(db_path)
    connection.execute("INSERT INTO person(name) VALUES ('Original')")
    connection.commit()
    before = db_path.read_bytes()
    invalid = tmp_path / "invalid.zip"
    invalid.write_bytes(b"not-a-zip")
    service = RestoreService(connection, db_path, tmp_path / "documents")
    with pytest.raises(InvalidBackupError):
        service.restore(invalid)
    connection.close()
    assert db_path.read_bytes() == before


def test_restore_empty_documents_removes_stale_current_files(tmp_path):
    source_db = tmp_path / "source.db"
    source = open_db(source_db)
    source.execute("INSERT INTO person(name) VALUES ('Do backup')")
    source.commit()
    empty_docs = tmp_path / "empty-docs"
    empty_docs.mkdir()
    backup = BackupService(source, source_db, empty_docs).create(tmp_path / "backups")
    source.close()

    live_db = tmp_path / "live.db"
    live = open_db(live_db)
    live.execute("INSERT INTO person(name) VALUES ('Antigo')")
    live.commit()
    live_docs = tmp_path / "live-documents"
    live_docs.mkdir()
    (live_docs / "arquivo-antigo.txt").write_text("stale", encoding="utf-8")

    result = RestoreService(live, live_db, live_docs).restore(backup.path)
    assert result.ok
    assert list(live_docs.rglob("*")) == []
    names = [r[0] for r in live.execute("SELECT name FROM person ORDER BY id")]
    assert names == ["Do backup"]
    live.close()


def test_restore_rejects_unknown_future_schema_migration(tmp_path):
    db_path = tmp_path / "source.db"
    connection = open_db(db_path)
    connection.execute("INSERT INTO schema_migrations(name) VALUES ('999_future.sql')")
    connection.commit()
    backup = BackupService(connection, db_path, tmp_path / "docs").create(tmp_path / "backups")
    connection.close()

    live_path = tmp_path / "live.db"
    live = open_db(live_path)
    service = RestoreService(live, live_path, tmp_path / "live-docs")
    with pytest.raises(InvalidBackupError, match="versão mais nova"):
        service.validate(backup.path)
    live.close()
