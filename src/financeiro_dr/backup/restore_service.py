from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile

from financeiro_dr.database.migrations import MigrationRunner


class InvalidBackupError(RuntimeError):
    pass


@dataclass(frozen=True)
class RestoreValidation:
    ok: bool
    created_at: str
    document_count: int


class RestoreService:
    def __init__(self, connection: sqlite3.Connection, database_file: Path, documents_dir: Path):
        self.connection = connection
        self.database_file = Path(database_file)
        self.documents_dir = Path(documents_dir)

    def _supported_migrations(self) -> set[str]:
        runner = MigrationRunner()
        return {p.name for p in runner.migrations_dir.glob("*.sql")}

    def _extract_validated(self, backup_zip: Path, root: Path):
        try:
            with zipfile.ZipFile(backup_zip) as archive:
                root_resolved = root.resolve()
                for info in archive.infolist():
                    output = (root / info.filename).resolve()
                    if output != root_resolved and root_resolved not in output.parents:
                        raise InvalidBackupError("Backup contém caminho inválido.")
                archive.extractall(root)
        except (OSError, zipfile.BadZipFile) as exc:
            raise InvalidBackupError("Arquivo de backup inválido.") from exc

        manifest_path = root / "manifest.json"
        database_path = root / "financeiro.db"
        if not manifest_path.exists() or not database_path.exists():
            raise InvalidBackupError("Backup incompleto.")

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InvalidBackupError("Manifesto do backup inválido.") from exc

        if manifest.get("version") != 1:
            raise InvalidBackupError("Versão de backup não suportada por este aplicativo.")
        if hashlib.sha256(database_path.read_bytes()).hexdigest() != manifest.get("database_sha256"):
            raise InvalidBackupError("Hash do banco não confere.")

        backup_db = sqlite3.connect(database_path)
        try:
            if backup_db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise InvalidBackupError("Banco do backup está corrompido.")
            table = backup_db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            ).fetchone()
            if table is None:
                raise InvalidBackupError("Backup sem informações de versão do banco.")
            applied = {row[0] for row in backup_db.execute("SELECT name FROM schema_migrations")}
            unknown = applied - self._supported_migrations()
            if unknown:
                raise InvalidBackupError(
                    "Este backup foi criado por uma versão mais nova do aplicativo. Atualize o programa antes de restaurar."
                )
        finally:
            backup_db.close()

        return manifest, database_path

    def validate(self, backup_zip: Path) -> RestoreValidation:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest, _ = self._extract_validated(Path(backup_zip), Path(temp_dir))
            return RestoreValidation(
                True,
                str(manifest.get("created_at", "")),
                int(manifest.get("document_count", 0)),
            )

    def restore(self, backup_zip: Path) -> RestoreValidation:
        # Validation happens before any write to the live database.
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest, restored_database = self._extract_validated(Path(backup_zip), root)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            self.database_file.parent.mkdir(parents=True, exist_ok=True)
            pre_restore_database = self.database_file.with_name(f"pre_restore_{timestamp}.db")
            pre_snapshot = sqlite3.connect(pre_restore_database)
            try:
                self.connection.backup(pre_snapshot)
            finally:
                pre_snapshot.close()

            self.documents_dir.parent.mkdir(parents=True, exist_ok=True)
            staged_documents = self.documents_dir.parent / f".{self.documents_dir.name}_restore_stage_{timestamp}"
            previous_documents = self.documents_dir.parent / f".{self.documents_dir.name}_pre_restore_{timestamp}"
            if staged_documents.exists():
                shutil.rmtree(staged_documents)
            restored_documents = root / "documents"
            if restored_documents.exists():
                shutil.copytree(restored_documents, staged_documents)
            else:
                staged_documents.mkdir(parents=True)

            database_replaced = False
            documents_moved = False
            try:
                source = sqlite3.connect(restored_database)
                try:
                    source.backup(self.connection)
                    self.connection.commit()
                    database_replaced = True
                finally:
                    source.close()

                if previous_documents.exists():
                    shutil.rmtree(previous_documents)
                if self.documents_dir.exists():
                    self.documents_dir.rename(previous_documents)
                    documents_moved = True
                staged_documents.rename(self.documents_dir)

                if previous_documents.exists():
                    shutil.rmtree(previous_documents)
                return RestoreValidation(
                    True,
                    str(manifest.get("created_at", "")),
                    int(manifest.get("document_count", 0)),
                )
            except Exception:
                # Restore the live DB from the safety snapshot if any later step fails.
                if database_replaced:
                    old_db = sqlite3.connect(pre_restore_database)
                    try:
                        old_db.backup(self.connection)
                        self.connection.commit()
                    finally:
                        old_db.close()
                if self.documents_dir.exists() and documents_moved:
                    shutil.rmtree(self.documents_dir)
                if previous_documents.exists():
                    previous_documents.rename(self.documents_dir)
                raise
            finally:
                if staged_documents.exists():
                    shutil.rmtree(staged_documents)
