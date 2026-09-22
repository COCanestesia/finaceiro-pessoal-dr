from datetime import date
import pytest
from financeiro_dr.audit.audit_service import AuditService
from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.repository import FinancialRepository
from financeiro_dr.core.financeiro.scheduling import SchedulingService,generate_installment_dates,next_monthly_date
from financeiro_dr.core.financeiro.service import FinancialService
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner

def test_monthly_recurrence_clamps_day_31():
    assert next_monthly_date(date(2026,1,31),31)==date(2026,2,28); assert next_monthly_date(date(2028,1,31),31)==date(2028,2,29)

def test_installment_dates_keep_preferred_day_after_short_month():
    assert generate_installment_dates(date(2026,1,31),3)==[date(2026,1,31),date(2026,2,28),date(2026,3,31)]

def test_installment_count_must_be_positive():
    with pytest.raises(ValueError,match="maior que zero"): generate_installment_dates(date(2026,1,10),0)

def test_create_installments_persists_group_numbers_and_dates(tmp_path):
    con=Database(tmp_path/"series.db").connect(); MigrationRunner().apply_all(con); repo=FinancialRepository(con); finance=FinancialService(con,repo,AuditService(con)); scheduling=SchedulingService(con,finance,repo); base=CreateEntry(description="Seguro anual",amount_cents=10000,entry_type="DESPESA",status="PENDENTE",competence_date=date(2026,1,31),due_date=date(2026,1,31))
    try:
        ids=scheduling.create_installments(base,3); entries=[repo.get(i) for i in ids]; assert [e.due_date for e in entries]==[date(2026,1,31),date(2026,2,28),date(2026,3,31)]; assert [e.installment_number for e in entries]==[1,2,3]; assert [e.installment_total for e in entries]==[3,3,3]; group_ids={e.installment_group_id for e in entries}; assert len(group_ids)==1; assert None not in group_ids
    finally: con.close()

def test_monthly_recurrence_materializes_future_entries_once(tmp_path):
    con=Database(tmp_path/"recurrence.db").connect(); MigrationRunner().apply_all(con); repo=FinancialRepository(con); finance=FinancialService(con,repo,AuditService(con)); scheduling=SchedulingService(con,finance,repo); base=CreateEntry(description="Mensalidade escola",amount_cents=300000,entry_type="DESPESA",status="PENDENTE",competence_date=date(2026,1,31),due_date=date(2026,1,31))
    try:
        first_id=scheduling.create_monthly_recurrence(base); first=repo.get(first_id); assert first is not None and first.is_recurring is True; assert first.recurrence_rule_id is not None; created=scheduling.materialize_recurrences_until(date(2026,3,31)); assert len(created)==2; assert [repo.get(i).due_date for i in created]==[date(2026,2,28),date(2026,3,31)]; assert scheduling.materialize_recurrences_until(date(2026,3,31))==[]; row=con.execute("select next_due_date from recurrence_rule where id=?",(first.recurrence_rule_id,)).fetchone(); assert row[0]=="2026-04-30"
    finally: con.close()
