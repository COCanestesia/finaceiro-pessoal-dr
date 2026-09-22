from datetime import date
import pytest
from financeiro_dr.audit.audit_service import AuditService
from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.repository import FinancialRepository
from financeiro_dr.core.financeiro.service import FinancialService,PossibleDuplicateError
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner

@pytest.fixture
def connection(tmp_path):
    con=Database(tmp_path/"finance.db").connect(); MigrationRunner().apply_all(con)
    try: yield con
    finally: con.close()
@pytest.fixture
def repo(connection): return FinancialRepository(connection)
@pytest.fixture
def service(connection,repo): return FinancialService(connection,repo,AuditService(connection))
def entry(**overrides):
    data=dict(description="Condomínio",amount_cents=150000,entry_type="DESPESA",status="PENDENTE",competence_date=date(2026,9,10),due_date=date(2026,9,10)); data.update(overrides); return CreateEntry(**data)

def test_transfer_is_not_counted_as_income_or_expense(service,repo):
    service.create_entry(entry(description="Mover",amount_cents=10000,entry_type="TRANSFERENCIA",status="PAGO")); totals=repo.month_totals(2026,9); assert totals.income_cents==0; assert totals.expense_cents==0

def test_create_entry_records_audit_in_same_transaction(service,connection):
    entry_id=service.create_entry(entry()); row=connection.execute("select action,snapshot_json from audit_log where entity='financial_entry' and entity_id=?",(entry_id,)).fetchone(); assert row is not None; assert row[0]=="CREATE"; assert '"amount_cents": 150000' in row[1]

def test_audit_failure_rolls_back_created_entry(connection,repo):
    audit=AuditService(connection)
    def fail(*args,**kwargs): raise RuntimeError("audit failed")
    audit.record_create=fail; service=FinancialService(connection,repo,audit)
    with pytest.raises(RuntimeError,match="audit failed"): service.create_entry(entry())
    assert connection.execute("select count(*) from financial_entry").fetchone()[0]==0

def test_update_entry_records_old_and_new_values(service,connection):
    entry_id=service.create_entry(entry()); service.update_entry(entry_id,{"amount_cents":175000,"description":"Condomínio casa"}); rows=connection.execute("select field_name,old_value,new_value from audit_log where entity_id=? and action='UPDATE' order by field_name",(entry_id,)).fetchall(); assert [tuple(row) for row in rows]==[("amount_cents","150000","175000"),("description","Condomínio","Condomínio casa")]

def test_soft_delete_keeps_record_and_audit(service,repo,connection):
    entry_id=service.create_entry(entry()); service.soft_delete(entry_id); assert repo.get(entry_id) is None; deleted=repo.get(entry_id,include_deleted=True); assert deleted is not None and deleted.deleted_at is not None; assert connection.execute("select action from audit_log where entity_id=? order by id desc limit 1",(entry_id,)).fetchone()[0]=="DELETE"

def test_possible_duplicate_uses_normalized_description_amount_and_one_day_window(service):
    original_id=service.create_entry(entry(description="  Escola   Filha  ",amount_cents=200000)); candidate=entry(description="escola filha",amount_cents=200000,competence_date=date(2026,9,11),due_date=date(2026,9,11)); duplicate=service.find_possible_duplicate(candidate); assert duplicate is not None; assert duplicate.id==original_id
    with pytest.raises(PossibleDuplicateError): service.create_entry(candidate)

def test_duplicate_entry_explicitly_allows_duplicate(service,repo):
    original_id=service.create_entry(entry(description="Seguro")); duplicate_id=service.duplicate_entry(original_id,due_date=date(2026,10,10)); assert duplicate_id!=original_id; duplicate=repo.get(duplicate_id); assert duplicate is not None; assert duplicate.description=="Seguro"; assert duplicate.due_date==date(2026,10,10)

def test_create_entries_batch_is_atomic_when_second_audit_fails(connection,repo):
    audit=AuditService(connection); calls=0; original=audit.record_create
    def fail_on_second(*args,**kwargs):
        nonlocal calls; calls+=1
        if calls==2: raise RuntimeError("audit failed on second")
        return original(*args,**kwargs)
    audit.record_create=fail_on_second; service=FinancialService(connection,repo,audit); commands=[entry(description="Parcela 1",allow_duplicate=True),entry(description="Parcela 2",allow_duplicate=True)]
    with pytest.raises(RuntimeError,match="second"): service.create_entries(commands)
    assert connection.execute("select count(*) from financial_entry").fetchone()[0]==0; assert connection.execute("select count(*) from audit_log").fetchone()[0]==0
