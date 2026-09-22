from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import sqlite3
from financeiro_dr.audit.audit_service import AuditService
from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.service import FinancialService

@dataclass(frozen=True)
class TransferResult:
    transfer_id:int; source_entry_id:int; target_entry_id:int

class BankService:
    def __init__(self, connection:sqlite3.Connection, finance_service:FinancialService|None=None, audit_service:AuditService|None=None):
        self.connection=connection; self.finance=finance_service or FinancialService(connection); self.audit=audit_service or AuditService(connection)
    def create_account(self,institution:str,name:str,opening_balance_cents:int=0)->int:
        if not institution.strip() or not name.strip(): raise ValueError("Informe instituição e nome da conta.")
        cur=self.connection.execute("INSERT INTO bank_account(institution,name,opening_balance_cents) VALUES (?,?,?)",(institution.strip(),name.strip(),opening_balance_cents)); ident=int(cur.lastrowid); self.audit.record_create("bank_account",ident,dict(self.connection.execute("SELECT * FROM bank_account WHERE id=?",(ident,)).fetchone())); self.connection.commit(); return ident
    def list_accounts(self,active_only:bool=True):
        q="SELECT * FROM bank_account"+(" WHERE active=1" if active_only else "")+" ORDER BY institution,name"; return [dict(r) for r in self.connection.execute(q)]
    def balance(self,account_id:int,at_date:date|None=None)->int:
        row=self.connection.execute("SELECT opening_balance_cents FROM bank_account WHERE id=?",(account_id,)).fetchone()
        if row is None: raise ValueError("Conta não encontrada.")
        params=[account_id]; date_sql=""
        if at_date: date_sql=" AND COALESCE(settled_date,competence_date)<=?"; params.append(at_date.isoformat())
        r=self.connection.execute("SELECT COALESCE(SUM(CASE WHEN entry_type='RECEITA' THEN amount_cents WHEN entry_type='DESPESA' THEN -amount_cents ELSE 0 END),0) FROM financial_entry WHERE bank_account_id=? AND deleted_at IS NULL AND status IN ('PAGO','RECEBIDO')"+date_sql,params).fetchone()
        tparams=[account_id,account_id]; tsql=""
        if at_date: tsql=" AND transfer_date<=?"; tparams.append(at_date.isoformat())
        tr=self.connection.execute("SELECT COALESCE(SUM(CASE WHEN target_account_id=? THEN amount_cents ELSE -amount_cents END),0) FROM internal_transfer WHERE (source_account_id=? OR target_account_id=?)"+tsql,([account_id,account_id,account_id]+([at_date.isoformat()] if at_date else []))).fetchone()
        return int(row[0])+int(r[0])+int(tr[0])
    def transfer(self,source_id:int,target_id:int,amount_cents:int,transfer_date:date,description:str)->TransferResult:
        if source_id==target_id: raise ValueError("Origem e destino devem ser diferentes.")
        if amount_cents<=0: raise ValueError("Valor deve ser maior que zero.")
        for ident in (source_id,target_id):
            if not self.connection.execute("SELECT 1 FROM bank_account WHERE id=? AND active=1",(ident,)).fetchone(): raise ValueError("Conta não encontrada ou inativa.")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            common=dict(description=description,amount_cents=amount_cents,entry_type="TRANSFERENCIA",status="PAGO",competence_date=transfer_date,settled_date=transfer_date,allow_duplicate=True)
            src=self.finance.create_entry(CreateEntry(**common,bank_account_id=source_id)); dst=self.finance.create_entry(CreateEntry(**common,bank_account_id=target_id))
            cur=self.connection.execute("INSERT INTO internal_transfer(source_account_id,target_account_id,amount_cents,transfer_date,description,source_entry_id,target_entry_id) VALUES (?,?,?,?,?,?,?)",(source_id,target_id,amount_cents,transfer_date.isoformat(),description,src,dst)); tid=int(cur.lastrowid); self.connection.commit(); return TransferResult(tid,src,dst)
        except Exception:
            if self.connection.in_transaction:self.connection.rollback()
            raise
