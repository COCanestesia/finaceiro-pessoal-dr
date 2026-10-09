from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QMessageBox,
)


class BankCardsPage(QWidget):
    def __init__(self, connection, parent=None):
        super().__init__(parent)
        self.connection = connection
        layout = QVBoxLayout(self)
        title = QLabel("Contas bancárias e cartões")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(title)
        layout.addWidget(QLabel("Cadastre contas e cartões. O saldo real e a conciliação serão configurados em etapa separada."))
        account_form = QFormLayout()
        self.bank_name = QLineEdit()
        self.bank_name.setPlaceholderText("Nome da conta")
        self.institution = QLineEdit()
        self.institution.setPlaceholderText("Instituição financeira")
        account_form.addRow("Conta:", self.bank_name)
        account_form.addRow("Banco:", self.institution)
        layout.addLayout(account_form)
        save_bank = QPushButton("Adicionar conta bancária")
        save_bank.clicked.connect(self.save_bank)
        layout.addWidget(save_bank)
        self.bank_table = QTableWidget(0, 3)
        self.bank_table.setHorizontalHeaderLabels(["ID", "Conta", "Instituição"])
        layout.addWidget(self.bank_table)

        card_form = QFormLayout()
        self.card_name = QLineEdit()
        self.card_name.setPlaceholderText("Nome do cartão")
        self.closing = QSpinBox()
        self.closing.setRange(1, 31)
        self.closing.setValue(1)
        self.due = QSpinBox()
        self.due.setRange(1, 31)
        self.due.setValue(10)
        card_form.addRow("Cartão:", self.card_name)
        card_form.addRow("Dia do fechamento:", self.closing)
        card_form.addRow("Dia do vencimento:", self.due)
        layout.addLayout(card_form)
        save_card = QPushButton("Adicionar cartão")
        save_card.clicked.connect(self.save_card)
        layout.addWidget(save_card)
        self.card_table = QTableWidget(0, 4)
        self.card_table.setHorizontalHeaderLabels(["ID", "Cartão", "Fechamento", "Vencimento"])
        layout.addWidget(self.card_table)
        self.refresh()

    def save_bank(self):
        name = self.bank_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Cadastro", "Informe o nome da conta.")
            return
        try:
            self.connection.execute(
                "INSERT INTO bank_account(name, institution) VALUES(?,?)",
                (name, self.institution.text().strip() or None),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))
            return
        self.bank_name.clear()
        self.institution.clear()
        self.refresh()

    def save_card(self):
        name = self.card_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Cadastro", "Informe o nome do cartão.")
            return
        try:
            self.connection.execute(
                "INSERT INTO credit_card(name, closing_day, due_day) VALUES(?,?,?)",
                (name, self.closing.value(), self.due.value()),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))
            return
        self.card_name.clear()
        self.refresh()

    def refresh(self):
        banks = self.connection.execute("SELECT id, name, institution FROM bank_account WHERE active=1 ORDER BY name,id").fetchall()
        self.bank_table.setRowCount(len(banks))
        for i, row in enumerate(banks):
            for j, val in enumerate(row):
                self.bank_table.setItem(i, j, QTableWidgetItem(str(val if val is not None else "")))
        cards = self.connection.execute("SELECT id, name, closing_day, due_day FROM credit_card WHERE active=1 ORDER BY name,id").fetchall()
        self.card_table.setRowCount(len(cards))
        for i, row in enumerate(cards):
            for j, val in enumerate(row):
                self.card_table.setItem(i, j, QTableWidgetItem(str(val)))
