from __future__ import annotations
from datetime import date
from PySide6.QtWidgets import QGridLayout,QLabel,QVBoxLayout,QWidget
from financeiro_dr.core.financeiro.dashboard import DashboardService
from financeiro_dr.core.financeiro.money import format_money

class DashboardPage(QWidget):
    def __init__(self,service:DashboardService,parent=None):
        super().__init__(parent); self.service=service; layout=QVBoxLayout(self); title=QLabel("Visão Geral"); title.setStyleSheet("font-size: 24px; font-weight: 700;"); layout.addWidget(title); self.grid=QGridLayout(); layout.addLayout(self.grid); layout.addStretch(1); self.refresh()
    def refresh(self)->None:
        while self.grid.count():
            item=self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        snap=self.service.snapshot(date.today()); cards=[("Receitas do mês",format_money(snap.income_cents)),("Despesas do mês",format_money(snap.expense_cents)),("Resultado",format_money(snap.result_cents)),("Atrasadas",str(snap.overdue_count)),("Pagar hoje",format_money(snap.pay_today_cents)),("Amanhã",format_money(snap.tomorrow_cents)),("Próx. 7 dias",format_money(snap.next_7_days_cents)),("Próx. 30 dias",format_money(snap.next_30_days_cents))]
        for index,(label,value) in enumerate(cards):
            box=QLabel(f"{label}\n{value}"); box.setStyleSheet("padding: 18px; border: 1px solid #d9dde3; border-radius: 8px; font-size: 16px;"); self.grid.addWidget(box,index//4,index%4)
