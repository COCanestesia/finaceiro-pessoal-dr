from __future__ import annotations
from datetime import date
from PySide6.QtWidgets import QGridLayout,QLabel,QVBoxLayout,QWidget
from financeiro_dr.core.financeiro.money import format_money
from financeiro_dr.core.financeiro.payables import PayablesService
from financeiro_dr.core.financeiro.repository import FinancialRepository

class DashboardPage(QWidget):
    def __init__(self,repository:FinancialRepository,payables:PayablesService,parent=None):
        super().__init__(parent); self.repository=repository; self.payables=payables; layout=QVBoxLayout(self); title=QLabel("Visão Geral"); title.setStyleSheet("font-size: 24px; font-weight: 700;"); layout.addWidget(title); self.grid=QGridLayout(); layout.addLayout(self.grid); layout.addStretch(1); self.refresh()
    def refresh(self)->None:
        while self.grid.count():
            item=self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        today=date.today(); totals=self.repository.month_totals(today.year,today.month); b=self.payables.buckets(today)
        cards=[("Receitas do mês",format_money(totals.income_cents)),("Despesas do mês",format_money(totals.expense_cents)),("Resultado",format_money(totals.result_cents)),("Atrasadas",str(len(b.overdue))),("Pagar hoje",format_money(sum(x.amount_cents for x in b.today))),("Amanhã",format_money(sum(x.amount_cents for x in b.tomorrow))),("Próx. 7 dias",format_money(sum(x.amount_cents for x in b.next_7_days))),("Próx. 30 dias",format_money(sum(x.amount_cents for x in b.next_30_days)))]
        for index,(label,value) in enumerate(cards):
            box=QLabel(f"{label}\n{value}"); box.setStyleSheet("padding: 18px; border: 1px solid #d9dde3; border-radius: 8px; font-size: 16px;"); self.grid.addWidget(box,index//4,index%4)
