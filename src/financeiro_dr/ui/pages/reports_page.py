from __future__ import annotations
from datetime import date
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QSpinBox,QComboBox,QPushButton,QFileDialog,QMessageBox
from financeiro_dr.core.financeiro.reports import export_pdf,export_excel

class ReportsPage(QWidget):
    def __init__(self,connection,parent=None):
        super().__init__(parent)
        self.connection=connection
        layout=QVBoxLayout(self)
        heading=QLabel("Relatórios financeiros")
        heading.setStyleSheet("font-size:24px;font-weight:700;")
        layout.addWidget(heading)
        layout.addWidget(QLabel("Resumo mensal por competência. Valores pendentes e realizados são detalhados por status."))
        self.year=QSpinBox()
        self.year.setRange(2000,2200)
        self.year.setValue(date.today().year)
        layout.addWidget(self.year)
        self.month=QComboBox()
        for month in range(1,13):
            self.month.addItem(f"{month:02d}",month)
        self.month.setCurrentIndex(date.today().month-1)
        layout.addWidget(self.month)
        for label,kind in (("Exportar PDF","pdf"),("Exportar Excel","xlsx")):
            button=QPushButton(label)
            button.clicked.connect(lambda checked=False,format=kind:self.save(format))
            layout.addWidget(button)
        layout.addStretch()

    def save(self,format):
        year=self.year.value()
        month=self.month.currentData()
        target,_=QFileDialog.getSaveFileName(self,"Salvar relatório",f"Relatorio-DR-{year}-{month:02d}.{format}",f"Arquivo {format.upper()} (*.{format})")
        if not target:return
        try:
            if format=="pdf": export_pdf(self.connection,target,year,month)
            else: export_excel(self.connection,target,year,month)
        except Exception as exc:
            QMessageBox.critical(self,"Erro ao gerar relatório",str(exc))
            return
        QMessageBox.information(self,"Relatório gerado",f"Relatório salvo em:\n{target}")
