from datetime import date,timedelta
import pytest
from financeiro_dr.audit.audit_service import AuditService
from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.payables import PayablesService
from financeiro_dr.core.financeiro.repository import FinancialRepository
from financeiro_dr.core.financeiro.service import FinancialService
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner

@pytest.fixture
def services(tmp_path):
    con=Database(tmp_path/"payables.db").connect(); MigrationRunner().apply_all(con); repo=FinancialRepository(con); finance=FinancialService(con,repo,AuditService(con)); payables=PayablesService(repo,finance)
    try: yield con,repo,finance,payables
    finally: con.close()
def add(finance,description,due,*,entry_type="DESPESA",status="PENDENTE",amount=10000):
    return finance.create_entry(CreateEntry(description=description,amount_cents=amount,entry_type=entry_type,status=status,competence_date=due,due_date=due,allow_duplicate=True))

def test_payable_buckets_are_mutually_exclusive(services):
    _,_,finance,payables=services; today=date(2026,9,22); add(finance,"Vencida",today-timedelta(days=1)); add(finance,"Hoje",today); add(finance,"Amanhã",today+timedelta(days=1)); add(finance,"Cinco dias",today+timedelta(days=5)); add(finance,"Vinte dias",today+timedelta(days=20)); add(finance,"Já paga",today,status="PAGO"); b=payables.buckets(today); assert [e.description for e in b.overdue]==["Vencida"]; assert [e.description for e in b.today]==["Hoje"]; assert [e.description for e in b.tomorrow]==["Amanhã"]; assert [e.description for e in b.next_7_days]==["Cinco dias"]; assert [e.description for e in b.next_30_days]==["Vinte dias"]

def test_receivable_buckets_and_settle_status(services):
    _,repo,finance,payables=services; today=date(2026,9,22); entry_id=add(finance,"Aluguel",today,entry_type="RECEITA",amount=250000); assert [e.id for e in payables.receivable_buckets(today).today]==[entry_id]; payables.settle(entry_id,today); entry=repo.get(entry_id); assert entry.status=="RECEBIDO"; assert entry.settled_date==today

def test_settle_expense_marks_paid(services):
    _,repo,finance,payables=services; today=date(2026,9,22); entry_id=add(finance,"Energia",today); payables.settle(entry_id,today); entry=repo.get(entry_id); assert entry.status=="PAGO"; assert entry.settled_date==today
