from datetime import date
from financeiro_dr.audit.audit_service import AuditService
from financeiro_dr.core.financeiro.agenda import AgendaService
from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.repository import FinancialRepository
from financeiro_dr.core.financeiro.service import FinancialService
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner

def test_month_groups_pending_payables_and_receivables_by_due_date(tmp_path):
    con=Database(tmp_path/"agenda.db").connect(); MigrationRunner().apply_all(con); repo=FinancialRepository(con); finance=FinancialService(con,repo,AuditService(con)); agenda=AgendaService(repo); day=date(2026,9,25)
    def create(description,amount,entry_type,status="PENDENTE"):
        finance.create_entry(CreateEntry(description=description,amount_cents=amount,entry_type=entry_type,status=status,competence_date=day,due_date=day,allow_duplicate=True))
    try:
        create("Escola",300000,"DESPESA"); create("Aluguel",450000,"RECEITA"); create("Cancelada",99999,"DESPESA","CANCELADO"); create("Paga",88888,"DESPESA","PAGO"); days=agenda.month(2026,9); target=next(item for item in days if item.day==day); assert target.pay_cents==300000; assert target.receive_cents==450000; assert len(target.entry_ids)==2
    finally: con.close()
