from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import sqlite3
from financeiro_dr.banking import BankService
from financeiro_dr.investments import InvestmentService

@dataclass(frozen=True)
class NetWorthSnapshot:
    bank_balances_cents:int; investments_cents:int; assets_cents:int; obligations_cents:int; net_worth_cents:int

class NetWorthService:
    def __init__(self,connection:sqlite3.Connection): self.connection=connection; self.banks=BankService(connection); self.investments=InvestmentService(connection)
    def snapshot(self,at_date:date)->NetWorthSnapshot:
        bank=sum(self.banks.balance(r['id'],at_date) for r in self.connection.execute('SELECT id FROM bank_account WHERE active=1'))
        inv=sum(self.investments.balance(r['id'],at_date) for r in self.connection.execute('SELECT id FROM investment_account WHERE active=1'))
        assets=int(self.connection.execute('SELECT COALESCE(SUM(estimated_value_cents),0) FROM asset WHERE active=1').fetchone()[0])
        obligations=int(self.connection.execute("SELECT COALESCE(SUM(amount_cents),0) FROM financial_entry WHERE entry_type='DESPESA' AND status IN ('PENDENTE','ATRASADO') AND deleted_at IS NULL AND due_date<=?",(at_date.isoformat(),)).fetchone()[0])
        return NetWorthSnapshot(bank,inv,assets,obligations,bank+inv+assets-obligations)
