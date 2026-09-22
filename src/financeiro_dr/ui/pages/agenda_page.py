from __future__ import annotations
from datetime import date
from PySide6.QtWidgets import QLabel,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget
from financeiro_dr.core.financeiro.agenda import AgendaService
from financeiro_dr.core.financeiro.money import format_money

class AgendaPage(QWidget):
    def __init__(self,service:AgendaService,parent=None):
        super().__init__(parent); self.service=service; layout=QVBoxLayout(self); layout.addWidget(QLabel("Agenda Financeira")); self.table=QTableWidget(0,3); self.table.setHorizontalHeaderLabels(["Dia","A pagar","A receber"]); layout.addWidget(self.table); self.refresh()
    def refresh(self)->None:
        today=date.today(); days=self.service.month(today.year,today.month); self.table.setRowCount(len(days))
        for row,item in enumerate(days):
            self.table.setItem(row,0,QTableWidgetItem(item.day.strftime("%d/%m/%Y"))); self.table.setItem(row,1,QTableWidgetItem(format_money(item.pay_cents))); self.table.setItem(row,2,QTableWidgetItem(format_money(item.receive_cents)))
