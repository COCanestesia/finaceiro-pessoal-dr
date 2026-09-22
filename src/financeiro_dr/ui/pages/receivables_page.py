from __future__ import annotations
from datetime import date
from PySide6.QtWidgets import QLabel,QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget
from financeiro_dr.core.financeiro.money import format_money
from financeiro_dr.core.financeiro.payables import PayablesService

class ReceivablesPage(QWidget):
    def __init__(self,service:PayablesService,parent=None):
        super().__init__(parent); self.service=service; self._entry_ids=[]; layout=QVBoxLayout(self); layout.addWidget(QLabel("Contas a Receber")); self.table=QTableWidget(0,4); self.table.setHorizontalHeaderLabels(["Vencimento","Descrição","Valor","Faixa"]); layout.addWidget(self.table); self.receive_button=QPushButton("Marcar como recebido"); self.receive_button.clicked.connect(self._settle_selected); layout.addWidget(self.receive_button); self.feedback_label=QLabel(""); layout.addWidget(self.feedback_label); self.refresh()
    def refresh(self)->None:
        b=self.service.receivable_buckets(date.today()); groups=(("Atrasada",b.overdue),("Hoje",b.today),("Amanhã",b.tomorrow),("Próx. 7 dias",b.next_7_days),("Próx. 30 dias",b.next_30_days)); rows=[(label,e) for label,entries in groups for e in entries]; self._entry_ids=[e.id for _,e in rows]; self.table.setRowCount(len(rows))
        for row,(label,e) in enumerate(rows):
            self.table.setItem(row,0,QTableWidgetItem(e.due_date.strftime("%d/%m/%Y") if e.due_date else "")); self.table.setItem(row,1,QTableWidgetItem(e.description)); self.table.setItem(row,2,QTableWidgetItem(format_money(e.amount_cents))); self.table.setItem(row,3,QTableWidgetItem(label))
    def _settle_selected(self)->None:
        row=self.table.currentRow()
        if row<0: self.feedback_label.setText("Selecione uma conta."); return
        try: self.service.settle(self._entry_ids[row],date.today())
        except Exception as exc: self.feedback_label.setText(str(exc)); return
        self.feedback_label.setText("Recebimento confirmado."); self.refresh()
