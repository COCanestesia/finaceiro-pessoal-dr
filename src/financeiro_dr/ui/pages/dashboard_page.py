from __future__ import annotations
from datetime import date
import sqlite3
from PySide6.QtWidgets import QGridLayout,QLabel,QVBoxLayout,QWidget
from financeiro_dr.core.financeiro.dashboard import DashboardService
from financeiro_dr.core.financeiro.money import format_money
from financeiro_dr.networth import NetWorthService
from financeiro_dr.budgets import BudgetService,BudgetAlertService
from financeiro_dr.reconciliation import ReconciliationService

class DashboardPage(QWidget):
    def __init__(self,service:DashboardService,connection:sqlite3.Connection|None=None,parent=None):
        super().__init__(parent);self.service=service;self.connection=connection;layout=QVBoxLayout(self);title=QLabel('Visão Geral');title.setStyleSheet('font-size:24px;font-weight:700;');layout.addWidget(title);self.grid=QGridLayout();layout.addLayout(self.grid);self.alerts=QLabel('');self.alerts.setWordWrap(True);layout.addWidget(self.alerts);layout.addStretch(1);self.refresh()
    def refresh(self):
        while self.grid.count():
            item=self.grid.takeAt(0)
            if item.widget():item.widget().deleteLater()
        snap=self.service.snapshot(date.today());cards=[('Receitas do mês',format_money(snap.income_cents)),('Despesas do mês',format_money(snap.expense_cents)),('Resultado',format_money(snap.result_cents)),('Atrasadas',str(snap.overdue_count)),('Pagar hoje',format_money(snap.pay_today_cents)),('Amanhã',format_money(snap.tomorrow_cents)),('Próx. 7 dias',format_money(snap.next_7_days_cents)),('Próx. 30 dias',format_money(snap.next_30_days_cents))]
        alerts=[]
        if self.connection is not None:
            try:
                nw=NetWorthService(self.connection).snapshot(date.today());cards += [('Patrimônio',format_money(nw.assets_cents)),('Investimentos',format_money(nw.investments_cents)),('Obrigações',format_money(nw.obligations_cents)),('Patrimônio Líquido',format_money(nw.net_worth_cents))]
                pending=ReconciliationService(self.connection).pending_count();cards.append(('Conciliações pendentes',str(pending)))
                balerts=BudgetAlertService(BudgetService(self.connection)).for_month(date.today().year,date.today().month)
                if balerts:alerts.append('Orçamentos em alerta: '+', '.join(f'#{a.budget_id} {a.percent:.1f}% ({a.level})' for a in balerts[:8]))
                used=int(self.connection.execute('SELECT COALESCE(SUM(amount_cents),0) FROM card_installment WHERE paid=0').fetchone()[0]);cards.append(('Cartões comprometidos',format_money(used)))
            except Exception as exc:alerts.append(f'Indicadores adicionais indisponíveis: {exc}')
        for i,(label,value) in enumerate(cards):
            box=QLabel(f'{label}\n{value}');box.setStyleSheet('padding:16px;border:1px solid #d9dde3;border-radius:8px;background:white;font-size:15px;');self.grid.addWidget(box,i//4,i%4)
        self.alerts.setText('\n'.join(alerts))
