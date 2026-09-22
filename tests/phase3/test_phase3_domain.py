from datetime import date
from pathlib import Path
import sqlite3
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.banking import BankService
from financeiro_dr.cards import CardService, invoice_period_for
from financeiro_dr.reconciliation import ImportService

def db():
 c=sqlite3.connect(':memory:'); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); MigrationRunner().apply_all(c); return c

def test_transfer_and_card_invoice(tmp_path):
 c=db(); b=BankService(c); a=b.create_account('Banco','A',10000); d=b.create_account('Banco','B',0); b.transfer(a,d,2500,date(2026,9,1),'Reserva'); assert b.balance(a)==7500 and b.balance(d)==2500
 cards=CardService(c); card=cards.create_card('Banco','Dr',10000,10,20); ids=cards.add_purchase(card,date(2026,9,11),'Compra',10000,3); inv=cards.invoice(card,2026,10); assert len(ids)==3 and inv.total_cents==3334
 assert invoice_period_for(date(2026,9,11),10)==(2026,10)

def test_csv_import_deduplicates(tmp_path):
 c=db(); aid=BankService(c).create_account('Banco','Conta'); p=tmp_path/'x.csv'; p.write_text('data,descricao,valor,id\n01/09/2026,Teste,-10,abc\n',encoding='utf-8'); svc=ImportService(c); first=svc.import_file(aid,p); second=svc.import_file(aid,p); assert first.created==1 and second.created==0 and second.duplicates==1
