from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import sqlite3
from financeiro_dr.audit.audit_service import AuditService

@dataclass(frozen=True)
class InvestmentSummary:
    balance_cents:int; contributions_cents:int; redemptions_cents:int; return_cents:int

class InvestmentService:
    TYPES={'APORTE','RESGATE','RENDIMENTO','AJUSTE'}
    def __init__(self,connection:sqlite3.Connection,audit_service:AuditService|None=None): self.connection=connection; self.audit=audit_service or AuditService(connection)
    def create(self,institution:str,account_name:str,investment_type:str)->int:
        cur=self.connection.execute('INSERT INTO investment_account(institution,account_name,investment_type) VALUES (?,?,?)',(institution,account_name,investment_type)); iid=int(cur.lastrowid); self.audit.record_create('investment_account',iid,dict(self.connection.execute('SELECT * FROM investment_account WHERE id=?',(iid,)).fetchone())); self.connection.commit(); return iid
    def add_movement(self,investment_id:int,movement_type:str,amount_cents:int,movement_date:date,notes:str|None=None)->int:
        if movement_type not in self.TYPES: raise ValueError('Tipo de movimento inválido.')
        if movement_type!='AJUSTE' and amount_cents<0: raise ValueError('Valor deve ser positivo.')
        if not self.connection.execute('SELECT 1 FROM investment_account WHERE id=? AND active=1',(investment_id,)).fetchone(): raise ValueError('Investimento não encontrado ou inativo.')
        cur=self.connection.execute('INSERT INTO investment_movement(investment_id,movement_type,amount_cents,movement_date,notes) VALUES (?,?,?,?,?)',(investment_id,movement_type,amount_cents,movement_date.isoformat(),notes)); mid=int(cur.lastrowid); self.audit.record_create('investment_movement',mid,dict(self.connection.execute('SELECT * FROM investment_movement WHERE id=?',(mid,)).fetchone())); self.connection.commit(); return mid
    def balance(self,investment_id:int,at_date:date|None=None)->int:
        q="SELECT COALESCE(SUM(CASE movement_type WHEN 'RESGATE' THEN -amount_cents ELSE amount_cents END),0) FROM investment_movement WHERE investment_id=?"; p=[investment_id]
        if at_date:q+=' AND movement_date<=?';p.append(at_date.isoformat())
        return int(self.connection.execute(q,p).fetchone()[0])
    def summary(self)->InvestmentSummary:
        row=self.connection.execute("SELECT COALESCE(SUM(CASE movement_type WHEN 'RESGATE' THEN -amount_cents ELSE amount_cents END),0),COALESCE(SUM(CASE WHEN movement_type='APORTE' THEN amount_cents ELSE 0 END),0),COALESCE(SUM(CASE WHEN movement_type='RESGATE' THEN amount_cents ELSE 0 END),0),COALESCE(SUM(CASE WHEN movement_type='RENDIMENTO' THEN amount_cents ELSE 0 END),0) FROM investment_movement").fetchone(); return InvestmentSummary(*(int(x) for x in row))
    def list_accounts(self): return [dict(r) for r in self.connection.execute('SELECT * FROM investment_account WHERE active=1 ORDER BY institution,account_name')]
