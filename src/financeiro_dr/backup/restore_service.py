from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import hashlib,json,shutil,sqlite3,tempfile,zipfile
class InvalidBackupError(RuntimeError):pass
@dataclass(frozen=True)
class RestoreValidation:
    ok:bool;created_at:str;document_count:int
class RestoreService:
    def __init__(self,connection:sqlite3.Connection,database_file:Path,documents_dir:Path):self.connection=connection;self.database_file=Path(database_file);self.documents_dir=Path(documents_dir)
    def _extract_validated(self,backup_zip:Path,root:Path):
        with zipfile.ZipFile(backup_zip) as z:
            for info in z.infolist():
                out=(root/info.filename).resolve()
                if root.resolve() not in out.parents and out!=root.resolve():raise InvalidBackupError('Backup contém caminho inválido.')
            z.extractall(root)
        manifest_path=root/'manifest.json';db=root/'financeiro.db'
        if not manifest_path.exists() or not db.exists():raise InvalidBackupError('Backup incompleto.')
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        if hashlib.sha256(db.read_bytes()).hexdigest()!=manifest.get('database_sha256'):raise InvalidBackupError('Hash do banco não confere.')
        con=sqlite3.connect(db)
        try:
            if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise InvalidBackupError('Banco do backup está corrompido.')
        finally:con.close()
        return manifest,db
    def validate(self,backup_zip:Path)->RestoreValidation:
        try:
            with tempfile.TemporaryDirectory() as td:
                manifest,_=self._extract_validated(Path(backup_zip),Path(td));return RestoreValidation(True,manifest.get('created_at',''),int(manifest.get('document_count',0)))
        except (OSError,zipfile.BadZipFile,KeyError,ValueError,json.JSONDecodeError) as exc:raise InvalidBackupError('Arquivo de backup inválido.') from exc
    def restore(self,backup_zip:Path):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);manifest,db=self._extract_validated(Path(backup_zip),root);pre=self.database_file.with_name(f'pre_restore_{datetime.now():%Y%m%d_%H%M%S}.db');snap=sqlite3.connect(pre);self.connection.backup(snap);snap.close();src=sqlite3.connect(db)
            try:src.backup(self.connection);self.connection.commit()
            finally:src.close()
            restored_docs=root/'documents'
            if restored_docs.exists():
                tempdocs=self.documents_dir.with_name(self.documents_dir.name+'_restore_tmp')
                if tempdocs.exists():shutil.rmtree(tempdocs)
                shutil.copytree(restored_docs,tempdocs)
                if self.documents_dir.exists():shutil.rmtree(self.documents_dir)
                tempdocs.rename(self.documents_dir)
            return RestoreValidation(True,manifest.get('created_at',''),int(manifest.get('document_count',0)))
