from __future__ import annotations

from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox,
)
from financeiro_dr.database.backup import create_backup, export_entries_csv


class SettingsPage(QWidget):
    def __init__(self, connection, parent=None):
        super().__init__(parent)
        self.connection = connection
        layout = QVBoxLayout(self)
        heading = QLabel("Backup e exportação")
        heading.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(heading)
        notice = QLabel(
            "O backup contém dados financeiros e acesso local. Guarde-o em local protegido. "
            "Nunca substitua o único backup existente."
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)
        backup = QPushButton("Criar backup completo (.db)")
        backup.clicked.connect(self._backup)
        layout.addWidget(backup)
        export = QPushButton("Exportar lançamentos (.csv)")
        export.clicked.connect(self._export)
        layout.addWidget(export)
        layout.addStretch()

    def _choose(self, name: str, filter_string: str) -> Path | None:
        result, _ = QFileDialog.getSaveFileName(self, "Salvar arquivo", name, filter_string)
        return Path(result) if result else None

    def _backup(self):
        name = f"FinanceiroDR-Backup-{datetime.now():%Y%m%d-%H%M%S}.db"
        path = self._choose(name, "Banco SQLite (*.db)")
        if path is None:
            return
        try:
            create_backup(self.connection, path)
        except Exception as exc:
            QMessageBox.critical(self, "Erro no backup", str(exc))
            return
        QMessageBox.information(self, "Backup concluído", f"Backup verificado e salvo em:\n{path}")

    def _export(self):
        name = f"FinanceiroDR-Lancamentos-{datetime.now():%Y%m%d-%H%M%S}.csv"
        path = self._choose(name, "Arquivo CSV (*.csv)")
        if path is None:
            return
        try:
            export_entries_csv(self.connection, path)
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao exportar", str(exc))
            return
        QMessageBox.information(self, "Exportação concluída", f"Lançamentos exportados em:\n{path}")
