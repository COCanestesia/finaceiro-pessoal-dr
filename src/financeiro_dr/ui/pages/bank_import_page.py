from __future__ import annotations

from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QComboBox,QPushButton,QFileDialog,QMessageBox,QTableWidget,QTableWidgetItem
from financeiro_dr.core.financeiro.bank_import import import_bank_csv
from financeiro_dr.core.financeiro.ofx_import import import_ofx
from financeiro_dr.core.financeiro.reconciliation import suggested_matches, confirm_match


class BankImportPage(QWidget):
    def __init__(self, connection, parent=None):
        super().__init__(parent)
        self.connection=connection
        layout=QVBoxLayout(self)
        title=QLabel("Extratos bancários")
        title.setStyleSheet("font-size:24px;font-weight:700;")
        layout.addWidget(title)
        tip=QLabel("Importação CSV segura: date, description, amount_cents. Valores em centavos, negativos para saídas. Os dados importados ainda não são conciliados automaticamente.")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        self.accounts=QComboBox()
        layout.addWidget(self.accounts)
        load=QPushButton("Importar arquivo CSV ou OFX")
        load.clicked.connect(self.import_file)
        layout.addWidget(load)
        self.table=QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels(["ID","Data","Descrição","Centavos","Situação"])
        layout.addWidget(self.table)
        reconcile=QPushButton("Conferir e conciliar lançamento selecionado")
        reconcile.clicked.connect(self.reconcile_selected)
        layout.addWidget(reconcile)
        refresh=QPushButton("Atualizar")
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh)
        self.refresh_accounts()

    def refresh_accounts(self):
        current=self.accounts.currentData()
        self.accounts.clear()
        for row in self.connection.execute("SELECT id,name FROM bank_account WHERE active=1 ORDER BY name"):
            self.accounts.addItem(row["name"],row["id"])
        index=self.accounts.findData(current)
        if index>=0: self.accounts.setCurrentIndex(index)
        self.refresh()

    def refresh(self):
        self.table.setRowCount(0)
        account=self.accounts.currentData()
        if account is None: return
        rows=self.connection.execute("SELECT id,posted_date,description,amount_cents,matched_entry_id FROM bank_statement_line WHERE account_id=? ORDER BY posted_date DESC,id DESC LIMIT 500",(account,)).fetchall()
        self.table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            values=[str(row[0]),row[1],row[2],str(row[3]),"Conciliado" if row[4] is not None else "Pendente"]
            for j,value in enumerate(values): self.table.setItem(i,j,QTableWidgetItem(value))

    def import_file(self):
        account=self.accounts.currentData()
        if account is None:
            QMessageBox.warning(self,"Importação","Cadastre uma conta bancária primeiro.")
            return
        name,_=QFileDialog.getOpenFileName(self,"Escolher extrato","","Extratos (*.csv *.ofx)")
        if not name: return
        try: result=import_ofx(self.connection,account,name) if name.lower().endswith('.ofx') else import_bank_csv(self.connection,account,name)
        except Exception as exc:
            QMessageBox.critical(self,"Erro ao importar",str(exc))
            return
        self.refresh()
        QMessageBox.information(self,"Importação concluída",f'Importados: {result["imported"]}. Repetidos ignorados: {result["duplicates"]}.')

    def reconcile_selected(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Conciliação", "Selecione uma movimentação.")
            return
        statement_id = int(self.table.item(selected, 0).text())
        try:
            candidates = suggested_matches(self.connection, statement_id)
            if not candidates:
                QMessageBox.information(self, "Conciliação", "Nenhum lançamento compatível encontrado.")
                return
            from PySide6.QtWidgets import QInputDialog
            labels = [f'{item["entry_id"]} | {item["description"]} | {item["amount_cents"]} centavos | diferença {item["days_apart"]} dia(s)' for item in candidates]
            choice, ok = QInputDialog.getItem(self, "Confirmar conciliação", "Selecione o lançamento correspondente:", labels, 0, False)
            if not ok:
                return
            index = labels.index(choice)
            result = QMessageBox.question(self, "Confirmar conciliação", "Confirma que a movimentação corresponde ao lançamento escolhido?")
            if result != QMessageBox.Yes:
                return
            confirm_match(self.connection, statement_id, candidates[index]["entry_id"])
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Erro de conciliação", str(exc))
