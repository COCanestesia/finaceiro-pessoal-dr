from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from calendar import monthrange
import sqlite3
from financeiro_dr.audit.audit_service import AuditService
from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.service import FinancialService
from .billing import invoice_period_for,split_cents

@dataclass(frozen=True)
class CardInvoice:
    card_id:int; year:int; month:int; total_cents:int; paid_cents:int
    @property
    def open_cents(self): return self.total_cents-self.paid_cents

class CardService:
    def __init__(self,connection:sqlite3.Connection,finance_service:FinancialService|None=None,audit_service:AuditService|None=None): self.connection=connection; self.finance=finance_service or FinancialService(connection); self.audit=audit_service or AuditService(connection)
    def create_card(self,issuer:str,holder:str,limit_cents:int,closing_day:int,due_day:int,name:str|None=None)->int:
        if limit_cents<0 or not 1<=closing_day<=31 or not 1<=due_day<=31: raise ValueError("Dados do cartão inválidos.")
        cur=self.connection.execute("INSERT INTO credit_card(issuer,holder,name,limit_cents,closing_day,due_day) VALUES (?,?,?,?,?,?)",(issuer,holder,name,limit_cents,closing_day,due_day)); cid=int(cur.lastrowid); self.audit.record_create("credit_card",cid,dict(self.connection.execute("SELECT * FROM credit_card WHERE id=?",(cid,)).fetchone())); self.connection.commit(); return cid
    def add_purchase(self,card_id:int,purchase_date:date,description:str,total_cents:int,installments:int=1,beneficiary_id=None,category_id=None,subcategory_id=None,cost_center_id=None)->list[int]:
        card=self.connection.execute("SELECT * FROM credit_card WHERE id=? AND active=1",(card_id,)).fetchone()
        if card is None: raise ValueError("Cartão não encontrado ou inativo.")
        amounts=split_cents(total_cents,installments); y,m=invoice_period_for(purchase_date,int(card['closing_day']))
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            cur=self.connection.execute("INSERT INTO card_purchase(card_id,purchase_date,description,total_cents,installments) VALUES (?,?,?,?,?)",(card_id,purchase_date.isoformat(),description,total_cents,installments)); pid=int(cur.lastrowid); ids=[]
            cy,cm=y,m
            for idx,amt in enumerate(amounts,1):
                due_day=min(int(card['due_day']),monthrange(cy,cm)[1]); due=date(cy,cm,due_day)
                cmd=CreateEntry(description=f"{description} ({idx}/{installments})",amount_cents=amt,entry_type="DESPESA",status="PENDENTE",competence_date=due,due_date=due,card_id=card_id,beneficiary_id=beneficiary_id,category_id=category_id,subcategory_id=subcategory_id,cost_center_id=cost_center_id,installment_number=idx,installment_total=installments,allow_duplicate=True)
                eid=self.finance.create_entry(cmd); ids.append(eid); self.connection.execute("INSERT INTO card_installment(purchase_id,installment_number,amount_cents,invoice_year,invoice_month,entry_id) VALUES (?,?,?,?,?,?)",(pid,idx,amt,cy,cm,eid))
                if cm==12: cy,cm=cy+1,1
                else: cm+=1
            self.connection.commit(); return ids
        except Exception:
            if self.connection.in_transaction:self.connection.rollback()
            raise
    def invoice(self,card_id:int,year:int,month:int)->CardInvoice:
        total=int(self.connection.execute("SELECT COALESCE(SUM(ci.amount_cents),0) FROM card_installment ci JOIN card_purchase cp ON cp.id=ci.purchase_id JOIN financial_entry fe ON fe.id=ci.entry_id WHERE cp.card_id=? AND ci.invoice_year=? AND ci.invoice_month=? AND fe.deleted_at IS NULL AND fe.status<>'CANCELADO'",(card_id,year,month)).fetchone()[0])
        paid=int(self.connection.execute("SELECT COALESCE(SUM(amount_cents),0) FROM card_invoice_payment WHERE card_id=? AND invoice_year=? AND invoice_month=?",(card_id,year,month)).fetchone()[0])
        return CardInvoice(card_id,year,month,total,paid)
    def used_limit_cents(self,card_id:int)->int:
        return int(self.connection.execute("SELECT COALESCE(SUM(ci.amount_cents),0) FROM card_installment ci JOIN card_purchase cp ON cp.id=ci.purchase_id JOIN financial_entry fe ON fe.id=ci.entry_id WHERE cp.card_id=? AND ci.paid=0 AND fe.status<>'CANCELADO' AND fe.deleted_at IS NULL",(card_id,)).fetchone()[0])
    def available_limit_cents(self,card_id:int)->int:
        row=self.connection.execute("SELECT limit_cents FROM credit_card WHERE id=?",(card_id,)).fetchone();
        if row is None: raise ValueError("Cartão não encontrado.")
        return int(row[0])-self.used_limit_cents(card_id)
