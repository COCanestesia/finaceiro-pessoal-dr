from __future__ import annotations

from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QComboBox,QPushButton,QFileDialog,QMessageBox,QTableWidget,QTableWidgetItem
from financeiro_dr.core.financeiro.bank_import import import_bank_csv
from financeiro_dr.core.financeiro.ofx_import import import_ofx


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
        load=QPushButton("Importar arquivo CSV")
        load.clicked.connect(self.import_file)
        layout.addWidget(load)
        self.table=QTableWidget(0,4)
        self.table.setHorizontalHeaderLabels(["Data","Descrição","Centavos","Situação"])
        layout.addWidget(self.table)
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
        rows=self.connection.execute("SELECT posted_date,description,amount_cents,matched_entry_id FROM bank_statement_line WHERE account_id=? ORDER BY posted_date DESC,id DESC LIMIT 500",(account,)).fetchall()
        self.table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            values=[row[0],row[1],str(row[2]),"Conciliado" if row[3] is not None else "Pendente"]
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
