from datetime import date
from financeiro_dr.audit.audit_service import AuditService
from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.repository import FinancialRepository
from financeiro_dr.core.financeiro.service import FinancialService
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner

def test_daily_flow_updates_dashboard(tmp_path):
    from financeiro_dr.core.financeiro.dashboard import DashboardService
    con=Database(tmp_path/"daily.db").connect(); MigrationRunner().apply_all(con); repo=FinancialRepository(con); finance=FinancialService(con,repo,AuditService(con)); dashboard=DashboardService(repo)
    try:
        finance.create_entry(CreateEntry(description="Condomínio",amount_cents=150000,entry_type="DESPESA",status="PENDENTE",competence_date=date.today(),due_date=date.today()))
        snap=dashboard.snapshot(date.today()); assert snap.pay_today_cents==150000; assert snap.overdue_count==0; assert snap.expense_cents==150000; assert snap.result_cents==-150000
    finally: con.close()
