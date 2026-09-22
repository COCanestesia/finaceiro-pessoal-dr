from dataclasses import dataclass
import sqlite3
from financeiro_dr.audit.audit_service import AuditService

@dataclass(frozen=True)
class IncomeSource:
    id:int; name:str; active:bool

class IncomeSourceService:
    def __init__(self,connection:sqlite3.Connection,audit_service:AuditService|None=None): self.connection=connection; self.audit=audit_service or AuditService(connection)
    def create(self,name:str)->int:
        name=name.strip()
        if not name: raise ValueError('Informe o nome da origem.')
        cur=self.connection.execute('INSERT INTO income_source(name) VALUES (?)',(name,)); iid=int(cur.lastrowid); self.audit.record_create('income_source',iid,dict(self.connection.execute('SELECT * FROM income_source WHERE id=?',(iid,)).fetchone())); self.connection.commit(); return iid
    def list_active(self)->list[IncomeSource]: return [IncomeSource(r['id'],r['name'],bool(r['active'])) for r in self.connection.execute('SELECT * FROM income_source WHERE active=1 ORDER BY name')]
    def list_all(self)->list[IncomeSource]: return [IncomeSource(r['id'],r['name'],bool(r['active'])) for r in self.connection.execute('SELECT * FROM income_source ORDER BY active DESC,name')]
    def set_active(self,item_id:int,active:bool)->None:
        before=self.connection.execute('SELECT * FROM income_source WHERE id=?',(item_id,)).fetchone()
        if before is None: raise ValueError('Origem não encontrada.')
        self.connection.execute("UPDATE income_source SET active=?,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",(1 if active else 0,item_id)); after=self.connection.execute('SELECT * FROM income_source WHERE id=?',(item_id,)).fetchone(); self.audit.record_update('income_source',item_id,dict(before),dict(after)); self.connection.commit()
