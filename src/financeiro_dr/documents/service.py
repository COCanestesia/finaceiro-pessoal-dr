from __future__ import annotations
from dataclasses import dataclass
from datetime import date,datetime
from pathlib import Path
import hashlib,mimetypes,shutil,sqlite3,re

@dataclass(frozen=True)
class DocumentFilters:
    start:date|None=None; end:date|None=None; person_id:int|None=None; category_id:int|None=None; document_type:str|None=None; entry_id:int|None=None; asset_id:int|None=None
@dataclass(frozen=True)
class DocumentRecord:
    id:int; original_name:str; document_type:str; relative_path:str|None; missing:bool; created_at:str

class DocumentService:
    def __init__(self,connection:sqlite3.Connection,storage_root:Path): self.connection=connection; self.storage_root=Path(storage_root); self.storage_root.mkdir(parents=True,exist_ok=True)
    def attach(self,source:Path,document_type:str,entry_id:int|None=None,asset_id:int|None=None,person_id:int|None=None)->int:
        source=Path(source)
        if not source.is_file(): raise ValueError('Arquivo não encontrado.')
        data=source.read_bytes(); sha=hashlib.sha256(data).hexdigest(); mime=mimetypes.guess_type(source.name)[0]
        self.connection.execute('BEGIN IMMEDIATE')
        dest=None
        try:
            cur=self.connection.execute('INSERT INTO document(original_name,sha256,size_bytes,mime_type,document_type,entry_id,asset_id,person_id) VALUES (?,?,?,?,?,?,?,?)',(source.name,sha,len(data),mime,document_type,entry_id,asset_id,person_id)); did=int(cur.lastrowid); now=datetime.now(); safe=re.sub(r'[^A-Za-z0-9._-]+','_',source.name); rel=Path(f'{now.year:04d}')/f'{now.month:02d}'/f'{did}_{sha[:8]}_{safe}'; dest=self.storage_root/rel; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,dest); self.connection.execute('UPDATE document SET stored_name=?,relative_path=? WHERE id=?',(dest.name,rel.as_posix(),did)); self.connection.commit(); return did
        except Exception:
            self.connection.rollback()
            if dest and dest.exists(): dest.unlink()
            raise
    def resolve_path(self,document_id:int)->Path|None:
        row=self.connection.execute('SELECT relative_path FROM document WHERE id=?',(document_id,)).fetchone()
        if row is None or not row[0]: return None
        path=self.storage_root/row[0]; return path if path.exists() else None
    def search(self,filters:DocumentFilters)->list[DocumentRecord]:
        q='SELECT d.* FROM document d LEFT JOIN financial_entry f ON f.id=d.entry_id WHERE 1=1'; p=[]
        for col,val in [('d.person_id',filters.person_id),('d.entry_id',filters.entry_id),('d.asset_id',filters.asset_id),('d.document_type',filters.document_type),('f.category_id',filters.category_id)]:
            if val is not None:q+=f' AND {col}=?';p.append(val)
        if filters.start:q+=' AND substr(d.created_at,1,10)>=?';p.append(filters.start.isoformat())
        if filters.end:q+=' AND substr(d.created_at,1,10)<=?';p.append(filters.end.isoformat())
        out=[]
        for r in self.connection.execute(q+' ORDER BY d.created_at DESC',p):
            missing=not bool(r['relative_path']) or not (self.storage_root/r['relative_path']).exists(); out.append(DocumentRecord(r['id'],r['original_name'],r['document_type'],r['relative_path'],missing,r['created_at']))
        return out
