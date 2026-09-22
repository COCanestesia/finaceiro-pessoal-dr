from __future__ import annotations
from datetime import date
import sqlite3
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QCheckBox,QComboBox,QDateEdit,QFormLayout,QGridLayout,QLabel,QLineEdit,QPushButton,QSpinBox,QTextEdit,QVBoxLayout,QWidget
from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.repository import FinancialRepository
from financeiro_dr.core.financeiro.scheduling import SchedulingService
from financeiro_dr.core.financeiro.service import FinancialService
from financeiro_dr.ui.widgets.money_edit import MoneyEdit

def _python_date(widget:QDateEdit)->date:
    v=widget.date();return date(v.year(),v.month(),v.day())
def _optional(combo:QComboBox):return combo.currentData() if combo.isEnabled() else None

class EntriesPage(QWidget):
    def __init__(self,finance_service:FinancialService,scheduling_service:SchedulingService,repository:FinancialRepository,connection:sqlite3.Connection|None=None,parent=None):
        super().__init__(parent);self.finance_service=finance_service;self.scheduling_service=scheduling_service;self.repository=repository;self.connection=connection
        layout=QVBoxLayout(self);title=QLabel('Lançamentos');title.setStyleSheet('font-size:24px;font-weight:700;');layout.addWidget(title);form=QFormLayout()
        self.type_combo=QComboBox();[(self.type_combo.addItem(a,b)) for a,b in [('Despesa','DESPESA'),('Receita','RECEITA'),('Transferência','TRANSFERENCIA'),('Investimento','INVESTIMENTO')]]
        self.description_input=QLineEdit();self.money_input=MoneyEdit();self.money_input.setPlaceholderText('0,00');self.competence_date=QDateEdit(QDate.currentDate());self.competence_date.setCalendarPopup(True);self.due_date=QDateEdit(QDate.currentDate());self.due_date.setCalendarPopup(True)
        self.status_combo=QComboBox();[(self.status_combo.addItem(a,b)) for a,b in [('Pendente','PENDENTE'),('Pago','PAGO'),('Recebido','RECEBIDO'),('Atrasado','ATRASADO'),('Cancelado','CANCELADO')]]
        self.payment_method_input=QLineEdit();self.notes_input=QTextEdit();self.notes_input.setMaximumHeight(80);self.recurring_check=QCheckBox('Repetir mensalmente');self.installments_spin=QSpinBox();self.installments_spin.setRange(1,120);self.installments_spin.setValue(1)
        self.nature_combo=QComboBox();self.nature_combo.addItem('Variável','VARIAVEL');self.nature_combo.addItem('Fixa','FIXA');self.income_source_combo=QComboBox()
        for label,widget in [('Tipo:',self.type_combo),('Descrição:',self.description_input),('Valor:',self.money_input),('Competência:',self.competence_date),('Vencimento:',self.due_date),('Status:',self.status_combo),('Natureza da despesa:',self.nature_combo),('Origem da receita:',self.income_source_combo),('Forma de pagamento:',self.payment_method_input),('Observação:',self.notes_input),('Recorrência:',self.recurring_check),('Parcelas:',self.installments_spin)]:form.addRow(label,widget)
        layout.addLayout(form);grid=QGridLayout();self.person_combo=QComboBox();self.category_combo=QComboBox();self.subcategory_combo=QComboBox();self.cost_center_combo=QComboBox();self.bank_combo=QComboBox();self.card_combo=QComboBox();self.asset_combo=QComboBox()
        for i,(label,combo) in enumerate([('Pessoa / Beneficiário',self.person_combo),('Categoria',self.category_combo),('Subcategoria',self.subcategory_combo),('Centro de Custo',self.cost_center_combo),('Conta',self.bank_combo),('Cartão',self.card_combo),('Patrimônio',self.asset_combo)]):grid.addWidget(QLabel(label),i//2*2,i%2*2);grid.addWidget(combo,i//2*2,i%2*2+1)
        layout.addLayout(grid);self.feedback_label=QLabel('');self.save_button=QPushButton('Salvar lançamento');self.save_button.clicked.connect(self._save);layout.addWidget(self.feedback_label);layout.addWidget(self.save_button);layout.addStretch(1)
        if connection is None:
            for combo in (self.person_combo,self.category_combo,self.subcategory_combo,self.cost_center_combo,self.bank_combo,self.card_combo,self.asset_combo,self.income_source_combo):combo.addItem('Disponível na próxima etapa');combo.setEnabled(False)
        else:
            self._load_refs();self.category_combo.currentIndexChanged.connect(self._load_subcategories)
        self.type_combo.currentIndexChanged.connect(self._update_type_fields);self._update_type_fields()
    def _load_combo(self,combo,sql,label):
        combo.clear();combo.addItem('Não informado',None)
        for r in self.connection.execute(sql):combo.addItem(label(r),r['id'])
    def _load_refs(self):
        self._load_combo(self.person_combo,"SELECT id,name FROM person WHERE active=1 ORDER BY name",lambda r:r['name']);self._load_combo(self.category_combo,"SELECT id,name FROM category WHERE active=1 ORDER BY name",lambda r:r['name']);self._load_combo(self.cost_center_combo,"SELECT id,name FROM cost_center WHERE active=1 ORDER BY name",lambda r:r['name']);self._load_combo(self.bank_combo,"SELECT id,institution,name FROM bank_account WHERE active=1 ORDER BY institution,name",lambda r:f"{r['institution']} - {r['name']}");self._load_combo(self.card_combo,"SELECT id,issuer,holder,name FROM credit_card WHERE active=1 ORDER BY issuer,holder",lambda r:f"{r['issuer']} - {r['name'] or r['holder']}");self._load_combo(self.asset_combo,"SELECT id,description FROM asset WHERE active=1 ORDER BY description",lambda r:r['description']);self._load_combo(self.income_source_combo,"SELECT id,name FROM income_source WHERE active=1 ORDER BY name",lambda r:r['name']);self._load_subcategories()
    def _load_subcategories(self):
        if self.connection is None:return
        self.subcategory_combo.clear();self.subcategory_combo.addItem('Não informado',None);cid=self.category_combo.currentData()
        if cid is not None:
            for r in self.connection.execute('SELECT id,name FROM subcategory WHERE category_id=? AND active=1 ORDER BY name',(cid,)):self.subcategory_combo.addItem(r['name'],r['id'])
    def _update_type_fields(self):
        kind=self.type_combo.currentData();self.nature_combo.setEnabled(kind=='DESPESA');self.income_source_combo.setEnabled(kind=='RECEITA' and self.connection is not None)
    def _save(self):
        self.feedback_label.clear()
        try:
            kind=self.type_combo.currentData();cmd=CreateEntry(description=self.description_input.text().strip(),amount_cents=self.money_input.cents(),entry_type=kind,status=self.status_combo.currentData(),competence_date=_python_date(self.competence_date),due_date=_python_date(self.due_date),payment_method=self.payment_method_input.text().strip() or None,notes=self.notes_input.toPlainText().strip() or None,beneficiary_id=_optional(self.person_combo),category_id=_optional(self.category_combo),subcategory_id=_optional(self.subcategory_combo),cost_center_id=_optional(self.cost_center_combo),bank_account_id=_optional(self.bank_combo),card_id=_optional(self.card_combo),asset_id=_optional(self.asset_combo),expense_nature=self.nature_combo.currentData() if kind=='DESPESA' else None,income_source_id=_optional(self.income_source_combo) if kind=='RECEITA' else None)
            n=self.installments_spin.value()
            if n>1:self.scheduling_service.create_installments(cmd,n)
            elif self.recurring_check.isChecked():self.scheduling_service.create_monthly_recurrence(cmd)
            else:self.finance_service.create_entry(cmd)
        except Exception as exc:self.feedback_label.setText(str(exc));return
        self.feedback_label.setText('Lançamento salvo com sucesso.');self.description_input.clear();self.money_input.clear()
