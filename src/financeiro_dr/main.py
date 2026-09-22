from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication,QDialog,QLabel
from financeiro_dr.app_paths import AppPaths
from financeiro_dr.audit.audit_service import AuditService
from financeiro_dr.core.financeiro.agenda import AgendaService
from financeiro_dr.core.financeiro.dashboard import DashboardService
from financeiro_dr.core.financeiro.payables import PayablesService
from financeiro_dr.core.financeiro.repository import FinancialRepository
from financeiro_dr.core.financeiro.scheduling import SchedulingService
from financeiro_dr.core.financeiro.service import FinancialService
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.security.auth_service import AuthService
from financeiro_dr.ui.app_window import MainWindow
from financeiro_dr.ui.login_dialog import LoginDialog
from financeiro_dr.ui.pages.agenda_page import AgendaPage
from financeiro_dr.ui.pages.dashboard_page import DashboardPage
from financeiro_dr.ui.pages.entries_page import EntriesPage
from financeiro_dr.ui.pages.payables_page import PayablesPage
from financeiro_dr.ui.pages.receivables_page import ReceivablesPage

def build_window(connection)->MainWindow:
    repo=FinancialRepository(connection); finance=FinancialService(connection,repo,AuditService(connection)); scheduling=SchedulingService(connection,finance,repo); payables=PayablesService(repo,finance); agenda=AgendaService(repo); window=MainWindow()
    window.add_page("dashboard","Início",DashboardPage(DashboardService(repo))); window.add_page("entries","Lançamentos",EntriesPage(finance,scheduling,repo)); window.add_page("payables","Contas a Pagar",PayablesPage(payables)); window.add_page("receivables","Contas a Receber",ReceivablesPage(payables)); window.add_page("agenda","Agenda Financeira",AgendaPage(agenda)); window.add_page("history","Histórico",QLabel("Histórico detalhado será ampliado nas próximas etapas.")); window.add_page("settings","Configurações",QLabel("Configurações completas entram na etapa de backup e instalador.")); return window

def main()->int:
    app=QApplication.instance() or QApplication(sys.argv); paths=AppPaths.from_environment(); connection=Database(paths.database_file).connect(); MigrationRunner().apply_all(connection); auth=AuthService(connection); login=LoginDialog(auth,setup_mode=not auth.has_password())
    if login.exec()!=QDialog.Accepted: connection.close(); return 0
    window=build_window(connection); window.show(); exit_code=app.exec(); connection.close(); return exit_code

if __name__ == "__main__": raise SystemExit(main())
