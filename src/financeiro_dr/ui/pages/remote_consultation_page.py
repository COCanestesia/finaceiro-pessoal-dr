from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QFormLayout, QComboBox, QDateEdit, QSpinBox,
)
from financeiro_dr.network.remote_client import RemoteReadClient


class RemoteConsultationPage(QWidget):
    """Authenticated remote consultation and authorized entry creation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.client = None
        layout = QVBoxLayout(self)
        title = QLabel("Financeiro no servidor central")
        title.setStyleSheet("font-size:24px;font-weight:700;")
        layout.addWidget(title)
        notice = QLabel("Conexão privada HTTPS. Apenas financeiro e administrador podem registrar novos lançamentos.")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        form = QFormLayout()
        self.address = QLineEdit()
        self.address.setPlaceholderText("https://servidor-privado")
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        form.addRow("Endereço seguro:", self.address)
        form.addRow("Usuário:", self.username)
        form.addRow("Senha:", self.password)
        layout.addLayout(form)
        connect = QPushButton("Conectar e consultar")
        connect.clicked.connect(self.connect_remote)
        layout.addWidget(connect)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Data", "Descrição", "Centavos", "Tipo", "Status"])
        layout.addWidget(self.table)

        editor = QFormLayout()
        self.entry_date = QDateEdit()
        self.entry_date.setCalendarPopup(True)
        self.entry_date.setDate(QDate.currentDate())
        self.description = QLineEdit()
        self.amount = QSpinBox()
        self.amount.setRange(1, 1000000000)
        self.amount.setSuffix(" centavos")
        self.entry_type = QComboBox()
        self.entry_type.addItem("Receita", "RECEITA")
        self.entry_type.addItem("Despesa", "DESPESA")
        self.entry_status = QComboBox()
        editor.addRow("Data:", self.entry_date)
        editor.addRow("Descrição:", self.description)
        editor.addRow("Valor:", self.amount)
        editor.addRow("Tipo:", self.entry_type)
        editor.addRow("Situação:", self.entry_status)
        layout.addLayout(editor)
        self.entry_type.currentIndexChanged.connect(self._update_status)
        self._update_status()
        self.save_button = QPushButton("Registrar no banco central")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_entry)
        layout.addWidget(self.save_button)

    def _update_status(self):
        self.entry_status.clear()
        self.entry_status.addItem("Pendente", "PENDENTE")
        if self.entry_type.currentData() == "RECEITA":
            self.entry_status.addItem("Recebido", "RECEBIDO")
        else:
            self.entry_status.addItem("Pago", "PAGO")

    def _display_rows(self, rows):
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, key in enumerate(("competence_date", "description", "amount_cents", "entry_type", "status")):
                self.table.setItem(i, j, QTableWidgetItem(str(row[key])))

    def connect_remote(self):
        self.client = None
        self.save_button.setEnabled(False)
        self.table.setRowCount(0)
        try:
            client = RemoteReadClient(self.address.text().strip())
            user = client.login(self.username.text().strip(), self.password.text())
            rows = client.entries()
        except Exception as exc:
            QMessageBox.warning(self, "Conexão não realizada", str(exc))
            return
        finally:
            self.password.clear()
        self.client = client
        self.save_button.setEnabled(user.get("role") in ("admin", "financeiro"))
        self._display_rows(rows)

    def save_entry(self):
        if self.client is None:
            QMessageBox.warning(self, "Servidor", "Conecte ao servidor primeiro.")
            return
        name = self.description.text().strip()
        if not name:
            QMessageBox.warning(self, "Dados incompletos", "Informe uma descrição.")
            return
        if QMessageBox.question(self, "Confirmar", "Registrar este lançamento no banco central?") != QMessageBox.Yes:
            return
        try:
            entry_id = self.client.create_entry(
                self.entry_date.date().toString("yyyy-MM-dd"),
                name, self.amount.value(), self.entry_type.currentData(),
                self.entry_status.currentData(),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Falha no lançamento", str(exc))
            return
        self.description.clear()
        try:
            self._display_rows(self.client.entries())
        except Exception:
            pass
        QMessageBox.information(self, "Registrado", f"Lançamento {entry_id} criado no servidor.")
