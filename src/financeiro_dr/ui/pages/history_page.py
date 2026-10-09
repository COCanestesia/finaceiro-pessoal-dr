from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem
from PySide6.QtCore import Qt


class HistoryPage(QWidget):
    def __init__(self, connection, parent=None):
        super().__init__(parent)
        self.connection = connection
        layout = QVBoxLayout(self)
        title = QLabel("Histórico de alterações")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(title)
        refresh = QPushButton("Atualizar histórico")
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Data e hora (UTC)", "Entidade", "Registro", "Ação", "Campo", "Valor anterior / novo"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        rows = self.connection.execute(
            "SELECT occurred_at, entity, entity_id, action, field_name, old_value, new_value "
            "FROM audit_log ORDER BY id DESC LIMIT 500"
        ).fetchall()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            values = [r["occurred_at"], r["entity"], str(r["entity_id"]), r["action"],
                      r["field_name"] or "", f'{r["old_value"] or ""} → {r["new_value"] or ""}']
            for j, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, j, item)
