from __future__ import annotations
from datetime import date
import sqlite3
from financeiro_dr.audit.audit_service import AuditService

class AssetService:
    TYPES={'IMOVEL','VEICULO','TERRENO','OUTRO'}
    def __init__(self,connection:sqlite3.Connection,audit_service:AuditService|None=None): self.connection=connection; self.audit=audit_service or AuditService(connection)
    def create(self,asset_type:str,description:str,acquisition_date:date|None,acquisition_value_cents:int,estimated_value_cents:int,notes:str|None=None)->int:
        if asset_type not in self.TYPES: raise ValueError('Tipo de patrimônio inválido.')
        if acquisition_value_cents<0 or estimated_value_cents<0: raise ValueError('Valores não podem ser negativos.')
        cur=self.connection.execute('INSERT INTO asset(asset_type,description,acquisition_date,acquisition_value_cents,estimated_value_cents,notes) VALUES (?,?,?,?,?,?)',(asset_type,description,acquisition_date.isoformat() if acquisition_date else None,acquisition_value_cents,estimated_value_cents,notes)); aid=int(cur.lastrowid); self.audit.record_create('asset',aid,dict(self.connection.execute('SELECT * FROM asset WHERE id=?',(aid,)).fetchone())); self.connection.commit(); return aid
    def update_estimated_value(self,asset_id:int,value_cents:int)->None:
        if value_cents<0: raise ValueError('Valor inválido.')
        before=self.connection.execute('SELECT * FROM asset WHERE id=?',(asset_id,)).fetchone()
        if before is None: raise ValueError('Patrimônio não encontrado.')
        self.connection.execute('BEGIN IMMEDIATE')
        try:
            self.connection.execute("UPDATE asset SET estimated_value_cents=?,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",(value_cents,asset_id)); after=self.connection.execute('SELECT * FROM asset WHERE id=?',(asset_id,)).fetchone(); self.audit.record_update('asset',asset_id,dict(before),dict(after)); self.connection.commit()
        except Exception:self.connection.rollback(); raise
    def list_active(self): return [dict(r) for r in self.connection.execute('SELECT * FROM asset WHERE active=1 ORDER BY asset_type,description')]
    def expenses(self,asset_id:int,start:date|None=None,end:date|None=None):
        q="SELECT * FROM financial_entry WHERE asset_id=? AND entry_type='DESPESA' AND deleted_at IS NULL AND status<>'CANCELADO'"; p=[asset_id]
        if start:q+=' AND competence_date>=?';p.append(start.isoformat())
        if end:q+=' AND competence_date<=?';p.append(end.isoformat())
        return [dict(r) for r in self.connection.execute(q,p)]
