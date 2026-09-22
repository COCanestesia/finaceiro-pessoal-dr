from datetime import date
import sqlite3
from financeiro_dr.banking import BankService
from financeiro_dr.cards import CardService
from financeiro_dr.reconciliation import ReconciliationService,CardReconciliationService

def extra_dashboard_metrics(connection:sqlite3.Connection,today:date):
    banks=BankService(connection);balance=sum(banks.balance(r['id'],today) for r in connection.execute('SELECT id FROM bank_account WHERE active=1'));cards=CardService(connection);invoice_open=0
    for r in connection.execute('SELECT id FROM credit_card WHERE active=1'):
        invoice_open+=sum(i.open_cents for i in cards.list_invoices(r['id']) if i.due_date and i.due_date<=date(today.year+1,12,31))
    pending=ReconciliationService(connection).pending_count()+CardReconciliationService(connection).pending_count();return balance,invoice_open,pending
