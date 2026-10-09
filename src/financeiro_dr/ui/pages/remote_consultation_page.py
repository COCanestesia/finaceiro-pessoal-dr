from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QFormLayout,
)
from financeiro_dr.network.remote_client import RemoteReadClient


class RemoteConsultationPage(QWidget):
    """Separate read-only consultation; never writes to the remote database."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client = None
        layout = QVBoxLayout(self)
        title = QLabel("Consulta em outro computador")
        title.setStyleSheet("font-size:24px;font-weight:700;")
        layout.addWidget(title)
        info = QLabel("Conecte por HTTPS ao servidor privado. A consulta não altera lançamentos.")
        info.setWordWrap(True)
        layout.addWidget(info)
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
        self.table.setHorizontalHeaderLabels(["Data", "Descrição", "Valor (centavos)", "Tipo", "Status"])
        layout.addWidget(self.table)

    def connect_remote(self):
        self.table.setRowCount(0)
        self.client = None
        try:
            client = RemoteReadClient(self.address.text().strip())
            client.login(self.username.text().strip(), self.password.text())
            self.password.clear()
            rows = client.entries()
        except Exception as exc:
            self.password.clear()
            QMessageBox.warning(self, "Conexão não realizada", str(exc))
            return
        self.client = client
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, key in enumerate(("competence_date", "description", "amount_cents", "entry_type", "status")):
                self.table.setItem(i, j, QTableWidgetItem(str(row[key])))
