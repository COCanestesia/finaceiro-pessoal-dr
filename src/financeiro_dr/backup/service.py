from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import hashlib,json,shutil,sqlite3,tempfile,zipfile
@dataclass(frozen=True)
class BackupResult:
    path:Path;created_at:datetime;document_count:int
class BackupService:
    def __init__(self,connection:sqlite3.Connection,database_file:Path,documents_dir:Path,config_file:Path|None=None):self.connection=connection;self.database_file=Path(database_file);self.documents_dir=Path(documents_dir);self.config_file=Path(config_file) if config_file else None
    def create(self,destination_dir:Path,reason:str='MANUAL')->BackupResult:
        if reason not in {'AUTO','MANUAL','PRE_RESTORE'}:raise ValueError('Motivo de backup inválido.')
        dest=Path(destination_dir);dest.mkdir(parents=True,exist_ok=True);now=datetime.now();name=f'FinanceiroPessoalDr_Backup_{now:%Y%m%d_%H%M%S}.zip';target=dest/name
        try:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td);db=root/'financeiro.db';snapshot=sqlite3.connect(db);self.connection.backup(snapshot);snapshot.close();dbhash=hashlib.sha256(db.read_bytes()).hexdigest();docs=root/'documents';count=0
                if self.documents_dir.exists():shutil.copytree(self.documents_dir,docs);count=sum(1 for p in docs.rglob('*') if p.is_file())
                config={}
                if self.config_file and self.config_file.exists():
                    try:config=json.loads(self.config_file.read_text(encoding='utf-8'))
                    except Exception:config={}
                (root/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8');manifest={'version':1,'created_at':now.isoformat(),'database_sha256':dbhash,'document_count':count};(root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
                with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
                    for p in root.rglob('*'):
                        if p.is_file():z.write(p,p.relative_to(root).as_posix())
            self.connection.execute("INSERT INTO backup_log(destination,reason,status,message,file_name) VALUES (?,?, 'SUCCESS','Backup concluído',?)",(str(dest),reason,name));self.connection.commit();return BackupResult(target,now,count)
        except Exception as exc:
            try:self.connection.execute("INSERT INTO backup_log(destination,reason,status,message,file_name) VALUES (?,?, 'ERROR',?,?)",(str(dest),reason,str(exc),name));self.connection.commit()
            except Exception:pass
            raise
    def last_success(self):return self.connection.execute("SELECT * FROM backup_log WHERE status='SUCCESS' ORDER BY id DESC LIMIT 1").fetchone()
