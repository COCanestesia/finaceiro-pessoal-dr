from __future__ import annotations
from datetime import date
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QCheckBox,QComboBox,QDateEdit,QFormLayout,QGridLayout,QLabel,QLineEdit,QPushButton,QSpinBox,QTextEdit,QVBoxLayout,QWidget
from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.repository import FinancialRepository
from financeiro_dr.core.financeiro.scheduling import SchedulingService
from financeiro_dr.core.financeiro.service import FinancialService
from financeiro_dr.ui.widgets.money_edit import MoneyEdit

def _python_date(widget:QDateEdit)->date:
    value=widget.date(); return date(value.year(),value.month(),value.day())

class EntriesPage(QWidget):
    def __init__(self,finance_service:FinancialService,scheduling_service:SchedulingService,repository:FinancialRepository,parent=None):
        super().__init__(parent); self.finance_service=finance_service; self.scheduling_service=scheduling_service; self.repository=repository
        layout=QVBoxLayout(self); title=QLabel("Lançamentos"); title.setStyleSheet("font-size: 24px; font-weight: 700;"); layout.addWidget(title); form=QFormLayout()
        self.type_combo=QComboBox()
        for label,value in (("Despesa","DESPESA"),("Receita","RECEITA"),("Transferência","TRANSFERENCIA"),("Investimento","INVESTIMENTO")): self.type_combo.addItem(label,value)
        self.description_input=QLineEdit(); self.money_input=MoneyEdit(); self.money_input.setPlaceholderText("0,00")
        self.competence_date=QDateEdit(QDate.currentDate()); self.competence_date.setCalendarPopup(True); self.due_date=QDateEdit(QDate.currentDate()); self.due_date.setCalendarPopup(True)
        self.status_combo=QComboBox()
        for label,value in (("Pendente","PENDENTE"),("Pago","PAGO"),("Recebido","RECEBIDO"),("Atrasado","ATRASADO"),("Cancelado","CANCELADO")): self.status_combo.addItem(label,value)
        self.payment_method_input=QLineEdit(); self.notes_input=QTextEdit(); self.notes_input.setMaximumHeight(90); self.recurring_check=QCheckBox("Repetir mensalmente"); self.installments_spin=QSpinBox(); self.installments_spin.setRange(1,120); self.installments_spin.setValue(1)
        for label,widget in (("Tipo:",self.type_combo),("Descrição:",self.description_input),("Valor:",self.money_input),("Competência:",self.competence_date),("Vencimento:",self.due_date),("Status:",self.status_combo),("Forma de pagamento:",self.payment_method_input),("Observação:",self.notes_input),("Recorrência:",self.recurring_check),("Parcelas:",self.installments_spin)): form.addRow(label,widget)
        layout.addLayout(form); future=QGridLayout()
        self.person_combo=QComboBox(); self.category_combo=QComboBox(); self.bank_combo=QComboBox(); self.card_combo=QComboBox()
        for combo in (self.person_combo,self.category_combo,self.bank_combo,self.card_combo): combo.addItem("Disponível na próxima etapa"); combo.setEnabled(False)
        future.addWidget(QLabel("Pessoa"),0,0); future.addWidget(self.person_combo,0,1); future.addWidget(QLabel("Categoria"),0,2); future.addWidget(self.category_combo,0,3); future.addWidget(QLabel("Conta"),1,0); future.addWidget(self.bank_combo,1,1); future.addWidget(QLabel("Cartão"),1,2); future.addWidget(self.card_combo,1,3); layout.addLayout(future)
        self.feedback_label=QLabel(""); self.save_button=QPushButton("Salvar lançamento"); self.save_button.clicked.connect(self._save); layout.addWidget(self.feedback_label); layout.addWidget(self.save_button); layout.addStretch(1)
    def _save(self)->None:
        self.feedback_label.clear()
        try:
            command=CreateEntry(description=self.description_input.text().strip(),amount_cents=self.money_input.cents(),entry_type=self.type_combo.currentData(),status=self.status_combo.currentData(),competence_date=_python_date(self.competence_date),due_date=_python_date(self.due_date),payment_method=self.payment_method_input.text().strip() or None,notes=self.notes_input.toPlainText().strip() or None)
            installments=self.installments_spin.value()
            if installments>1: self.scheduling_service.create_installments(command,installments)
            elif self.recurring_check.isChecked(): self.scheduling_service.create_monthly_recurrence(command)
            else: self.finance_service.create_entry(command)
        except Exception as exc: self.feedback_label.setText(str(exc)); return
        self.feedback_label.setText("Lançamento salvo com sucesso."); self.description_input.clear(); self.money_input.clear()
