from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog, QLabel

from financeiro_dr.app_paths import AppPaths
from financeiro_dr.audit.audit_service import AuditService
from financeiro_dr.core.financeiro.agenda import AgendaService
from financeiro_dr.core.financeiro.dashboard import DashboardService
from financeiro_dr.core.financeiro.payables import PayablesService
from financeiro_dr.core.financeiro.repository import FinancialRepository
from financeiro_dr.core.financeiro.scheduling import SchedulingService
from financeiro_dr.core.financeiro.service import FinancialService
from financeiro_dr.database.connection import Database
from financeiro_dr.database.backup import automatic_daily_backup
from financeiro_dr.database.restore import restore_backup_offline
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.security.auth_service import AuthService
from financeiro_dr.ui.app_window import MainWindow
from financeiro_dr.ui.login_dialog import LoginDialog
from financeiro_dr.ui.pages.agenda_page import AgendaPage
from financeiro_dr.ui.pages.dashboard_page import DashboardPage
from financeiro_dr.ui.pages.entries_page import EntriesPage
from financeiro_dr.ui.pages.payables_page import PayablesPage
from financeiro_dr.ui.pages.receivables_page import ReceivablesPage
from financeiro_dr.ui.pages.settings_page import SettingsPage
from financeiro_dr.ui.pages.history_page import HistoryPage
from financeiro_dr.ui.pages.bank_cards_page import BankCardsPage
from financeiro_dr.ui.pages.bank_import_page import BankImportPage
from financeiro_dr.ui.pages.reports_page import ReportsPage


def build_window(connection) -> MainWindow:
    repo = FinancialRepository(connection)
    finance = FinancialService(connection, repo, AuditService(connection))
    scheduling = SchedulingService(connection, finance, repo)
    payables = PayablesService(repo, finance)
    agenda = AgendaService(repo)
    window = MainWindow()
    window.add_page("dashboard", "Início", DashboardPage(DashboardService(repo)))
    window.add_page("entries", "Lançamentos", EntriesPage(finance, scheduling, repo))
    window.add_page("payables", "Contas a Pagar", PayablesPage(payables))
    window.add_page("receivables", "Contas a Receber", ReceivablesPage(payables))
    window.add_page("agenda", "Agenda Financeira", AgendaPage(agenda))
    window.add_page("banks", "Bancos e Cartões", BankCardsPage(connection))
    window.add_page("statements", "Extratos", BankImportPage(connection))
    window.add_page("reports", "Relatórios", ReportsPage(connection))
    window.add_page("history", "Histórico", HistoryPage(connection))
    window.add_page("settings", "Configurações", SettingsPage(connection))
    return window


def _open_database():
    paths = AppPaths.from_environment()
    connection = Database(paths.database_file).connect()
    MigrationRunner().apply_all(connection)
    try:
        automatic_daily_backup(connection, paths.data_dir / 'backups')
    except Exception:
        connection.close()
        raise
    return paths, connection


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if '--restore-backup' in args:
        index = args.index('--restore-backup')
        if len(args) != index + 2:
            raise ValueError('Informe o caminho do backup após --restore-backup.')
        destination = AppPaths.from_environment().database_file
        restore_backup_offline(Path(args[index + 1]), destination)
        return 0
    _, connection = _open_database()

    if "--smoke-test" in args:
        connection.execute("SELECT 1").fetchone()
        connection.close()
        return 0

    app = QApplication.instance() or QApplication([sys.argv[0], *args])
    auth = AuthService(connection)
    login = LoginDialog(auth, setup_mode=not auth.has_password())
    if login.exec() != QDialog.Accepted:
        connection.close()
        return 0

    window = build_window(connection)
    window.show()
    exit_code = app.exec()
    connection.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
