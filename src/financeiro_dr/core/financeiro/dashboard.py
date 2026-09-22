from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from financeiro_dr.core.financeiro.repository import FinancialRepository

@dataclass(frozen=True)
class DashboardSnapshot:
    income_cents: int
    expense_cents: int
    result_cents: int
    overdue_count: int
    pay_today_cents: int
    tomorrow_cents: int
    next_7_days_cents: int
    next_30_days_cents: int

class DashboardService:
    def __init__(self, repository: FinancialRepository):
        self.repository = repository
    def snapshot(self, today: date) -> DashboardSnapshot:
        totals = self.repository.month_totals(today.year, today.month)
        entries = self.repository.list_unsettled_due("DESPESA", end_date=today + timedelta(days=30))
        overdue_count=0; pay_today=0; tomorrow=0; next_7=0; next_30=0
        for entry in entries:
            if entry.due_date is None: continue
            delta=(entry.due_date-today).days
            if delta<0: overdue_count+=1
            elif delta==0: pay_today+=entry.amount_cents
            elif delta==1: tomorrow+=entry.amount_cents
            elif 2<=delta<=7: next_7+=entry.amount_cents
            elif 8<=delta<=30: next_30+=entry.amount_cents
        return DashboardSnapshot(totals.income_cents, totals.expense_cents, totals.result_cents, overdue_count, pay_today, tomorrow, next_7, next_30)
