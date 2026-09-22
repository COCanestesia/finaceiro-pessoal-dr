from __future__ import annotations
import sqlite3
from financeiro_dr.audit.audit_service import AuditService
from .models import BudgetSnapshot

class BudgetService:
    def __init__(self, connection: sqlite3.Connection, audit_service: AuditService | None=None): self.connection=connection; self.audit=audit_service or AuditService(connection)
    def create(self, month:str, amount_cents:int, person_id=None, category_id=None, cost_center_id=None)->int:
        try: year, mon = map(int, month.split("-"))
        except Exception as exc: raise ValueError("Mês deve estar no formato AAAA-MM.") from exc
        if mon<1 or mon>12 or amount_cents<0: raise ValueError("Orçamento inválido.")
        exists=self.connection.execute("SELECT id FROM budget WHERE year=? AND month=? AND person_id IS ? AND category_id IS ? AND cost_center_id IS ? AND active=1",(year,mon,person_id,category_id,cost_center_id)).fetchone()
        if exists: raise ValueError("Já existe orçamento para este escopo no mês.")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            cur=self.connection.execute("INSERT INTO budget(year,month,amount_cents,person_id,category_id,cost_center_id) VALUES (?,?,?,?,?,?)",(year,mon,amount_cents,person_id,category_id,cost_center_id)); bid=int(cur.lastrowid)
            self.audit.record_create("budget",bid,dict(self.connection.execute("SELECT * FROM budget WHERE id=?",(bid,)).fetchone())); self.connection.commit(); return bid
        except Exception: self.connection.rollback(); raise
    def snapshot(self,budget_id:int)->BudgetSnapshot:
        b=self.connection.execute("SELECT * FROM budget WHERE id=?",(budget_id,)).fetchone()
        if b is None: raise ValueError("Orçamento não encontrado.")
        sql="SELECT COALESCE(SUM(amount_cents),0) FROM financial_entry WHERE entry_type='DESPESA' AND status<>'CANCELADO' AND deleted_at IS NULL AND competence_date LIKE ?"
        params=[f"{b['year']:04d}-{b['month']:02d}-%"]
        for col in ("beneficiary_id","category_id","cost_center_id"):
            key={"beneficiary_id":"person_id","category_id":"category_id","cost_center_id":"cost_center_id"}[col]; value=b[key]
            if value is not None: sql+=f" AND {col}=?"; params.append(value)
        spent=int(self.connection.execute(sql,params).fetchone()[0])
        return BudgetSnapshot(int(b['id']),int(b['year']),int(b['month']),int(b['amount_cents']),b['person_id'],b['category_id'],b['cost_center_id'],spent)
    def month_summary(self,year:int,month:int)->list[BudgetSnapshot]:
        ids=[r[0] for r in self.connection.execute("SELECT id FROM budget WHERE year=? AND month=? AND active=1 ORDER BY id",(year,month))]
        return [self.snapshot(i) for i in ids]
