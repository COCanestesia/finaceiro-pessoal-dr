from __future__ import annotations

from datetime import date
import sys

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from financeiro_dr.app_paths import AppPaths
from financeiro_dr.audit.audit_service import AuditService
from financeiro_dr.backup import BackupService, RestoreService
from financeiro_dr.classification import ClassificationService
from financeiro_dr.core.financeiro.agenda import AgendaService
from financeiro_dr.core.financeiro.dashboard import DashboardService
from financeiro_dr.core.financeiro.payables import PayablesService
from financeiro_dr.core.financeiro.repository import FinancialRepository
from financeiro_dr.core.financeiro.scheduling import SchedulingService
from financeiro_dr.core.financeiro.service import FinancialService
from financeiro_dr.database.connection import Database
from financeiro_dr.database.health import DatabaseHealth
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.documents import DocumentService
from financeiro_dr.people import PeopleService
from financeiro_dr.security.auth_service import AuthService
from financeiro_dr.settings import SettingsService
from financeiro_dr.ui.app_window import MainWindow
from financeiro_dr.ui.login_dialog import LoginDialog
from financeiro_dr.ui.pages.agenda_page import AgendaPage
from financeiro_dr.ui.pages.dashboard_page import DashboardPage
from financeiro_dr.ui.pages.entries_page import EntriesPage
from financeiro_dr.ui.pages.payables_page import PayablesPage
from financeiro_dr.ui.pages.receivables_page import ReceivablesPage
from financeiro_dr.ui.pages.full_pages import (
    AssetsPage,
    AuditHistoryPage,
    BackupPage,
    BanksPage,
    BudgetsPage,
    CardsPage,
    ClassificationPage,
    DocumentsPage,
    InvestmentsPage,
    PeoplePage,
    ReconciliationPage,
    ReportsPage,
    SettingsPage,
)


def build_window(connection, paths: AppPaths | None = None) -> MainWindow:
    paths = paths or AppPaths.from_environment()
    repo = FinancialRepository(connection)
    audit = AuditService(connection)
    finance = FinancialService(connection, repo, audit)
    scheduling = SchedulingService(connection, finance, repo)
    payables = PayablesService(repo, finance)
    agenda = AgendaService(repo)
    config_file = paths.config_dir / "config.json"
    settings = SettingsService(config_file)
    documents = DocumentService(connection, paths.documents_dir)
    backup = BackupService(connection, paths.database_file, paths.documents_dir, config_file)
    restore = RestoreService(connection, paths.database_file, paths.documents_dir)
    auth = AuthService(connection)

    window = MainWindow()
    window.add_page("dashboard", "Início", DashboardPage(DashboardService(repo), connection))
    window.add_page("entries", "Lançamentos", EntriesPage(finance, scheduling, repo, connection))
    window.add_page("payables", "Contas a Pagar", PayablesPage(payables))
    window.add_page("receivables", "Contas a Receber", ReceivablesPage(payables))
    window.add_page("agenda", "Agenda Financeira", AgendaPage(agenda))
    window.add_page("people", "Pessoas / Beneficiários", PeoplePage(PeopleService(connection)))
    window.add_page("classification", "Categorias e Centros", ClassificationPage(connection, ClassificationService(connection)))
    window.add_page("budgets", "Orçamentos", BudgetsPage(connection))
    window.add_page("banks", "Bancos e Contas", BanksPage(connection))
    window.add_page("cards", "Cartões", CardsPage(connection))
    window.add_page("reconciliation", "Conciliação", ReconciliationPage(connection))
    window.add_page("assets", "Patrimônio", AssetsPage(connection))
    window.add_page("investments", "Investimentos", InvestmentsPage(connection))
    window.add_page("documents", "Documentos", DocumentsPage(connection, documents))
    window.add_page("reports", "Relatórios", ReportsPage(connection))
    window.add_page("history", "Histórico", AuditHistoryPage(connection))
    window.add_page("backup", "Backup", BackupPage(backup, restore, settings))
    window.add_page("settings", "Configurações", SettingsPage(settings, auth))
    return window


def _open_database():
    paths = AppPaths.from_environment()
    connection = Database(paths.database_file).connect()
    MigrationRunner().apply_all(connection)
    return paths, connection


def _run_automatic_backup(paths: AppPaths, connection) -> None:
    settings_service = SettingsService(paths.config_dir / "config.json")
    settings = settings_service.load()
    if not settings.auto_backup_enabled or not settings.backup_dir:
        return
    today = date.today().isoformat()
    last = connection.execute(
        "SELECT substr(created_at,1,10) FROM backup_log WHERE status='SUCCESS' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if last and last[0] == today:
        return
    BackupService(
        connection,
        paths.database_file,
        paths.documents_dir,
        paths.config_dir / "config.json",
    ).create(settings.backup_dir, "AUTO")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    paths, connection = _open_database()
    health = DatabaseHealth.check(connection)

    if "--smoke-test" in args:
        connection.close()
        return 0 if health.ok else 2

    app = QApplication.instance() or QApplication([sys.argv[0], *args])
    if not health.ok:
        QMessageBox.critical(None, "Financeiro Pessoal do Dr.", health.message)
        connection.close()
        return 2

    auth = AuthService(connection)
    login = LoginDialog(auth, setup_mode=not auth.has_password())
    if login.exec() != QDialog.Accepted:
        connection.close()
        return 0

    try:
        _run_automatic_backup(paths, connection)
    except Exception as exc:
        QMessageBox.warning(
            None,
            "Backup automático",
            "Não foi possível fazer o backup automático. O sistema continuará funcionando.\n\n" + str(exc),
        )

    window = build_window(connection, paths)
    window.show()
    exit_code = app.exec()
    connection.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
