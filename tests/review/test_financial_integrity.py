from datetime import date
import sqlite3
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.banking import BankService
from financeiro_dr.cards import CardService,invoice_due_date
from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.repository import FinancialRepository
from financeiro_dr.core.financeiro.scheduling import SchedulingService
from financeiro_dr.core.financeiro.service import FinancialService
from financeiro_dr.reconciliation import ReconciliationService

def db():
 c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');MigrationRunner().apply_all(c);return c

def test_invoice_payment_reduces_bank_without_double_counting_expense():
 c=db();b=BankService(c);aid=b.create_account('Banco','Conta',100000);cards=CardService(c);cid=cards.create_card('Banco','Dr',50000,25,5);cards.add_purchase(cid,date(2026,9,20),'Mercado',10000,1);inv=cards.invoice(cid,2026,9);assert inv.due_date==date(2026,10,5);cards.pay_invoice(cid,2026,9,aid,date(2026,10,5));assert b.balance(aid)==90000;assert FinancialRepository(c).month_totals(2026,10).expense_cents==10000;assert cards.available_limit_cents(cid)==50000

def test_reconciliation_never_suggests_other_account_or_wrong_sign():
 c=db();b=BankService(c);a=b.create_account('Banco','A');other=b.create_account('Banco','B');f=FinancialService(c);wrong=f.create_entry(CreateEntry('Mesmo',1000,'DESPESA','PAGO',date(2026,9,1),bank_account_id=other));right=f.create_entry(CreateEntry('Mesmo',1000,'RECEITA','RECEBIDO',date(2026,9,1),bank_account_id=a));imp=c.execute("INSERT INTO statement_import(account_id,source_name,row_count) VALUES (?,'x',1)",(a,)).lastrowid;sid=c.execute("INSERT INTO statement_row(import_id,account_id,posted_date,amount_cents,description,raw_hash) VALUES (?,?,?,?,'Mesmo','h')",(imp,a,'2026-09-01',1000)).lastrowid;c.commit();ids=[x.entry_id for x in ReconciliationService(c).suggest(sid).candidates];assert right in ids and wrong not in ids

def test_recurrence_preserves_classification_fields():
 c=db();cur=c.execute("INSERT INTO asset(asset_type,description,estimated_value_cents) VALUES ('OUTRO','Bem',100)");asset=int(cur.lastrowid);c.commit();f=FinancialService(c);r=FinancialRepository(c);s=SchedulingService(c,f,r);first=s.create_monthly_recurrence(CreateEntry('Conta',1000,'DESPESA','PENDENTE',date(2026,9,1),due_date=date(2026,9,10),asset_id=asset,expense_nature='FIXA'));s.materialize_recurrences_until(date(2026,10,10));rows=c.execute("SELECT asset_id,expense_nature FROM financial_entry WHERE recurrence_rule_id=(SELECT recurrence_rule_id FROM financial_entry WHERE id=?) ORDER BY id",(first,)).fetchall();assert len(rows)==2 and all(x['asset_id']==asset and x['expense_nature']=='FIXA' for x in rows)
