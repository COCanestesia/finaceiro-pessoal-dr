import json
from datetime import date
import pytest
from financeiro_dr.audit.audit_service import AuditService
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner

@pytest.fixture
def connection(tmp_path):
    con=Database(tmp_path/"audit.db").connect(); MigrationRunner().apply_all(con)
    try: yield con
    finally: con.close()
@pytest.fixture
def audit_service(connection): return AuditService(connection)

def test_update_records_old_and_new_values(audit_service,connection):
    audit_service.record_update("financial_entry",10,{"amount_cents":200000},{"amount_cents":250000}); row=connection.execute("select field_name, old_value, new_value from audit_log where entity_id=10").fetchone(); assert tuple(row)==("amount_cents","200000","250000")

def test_update_records_only_changed_fields(audit_service,connection):
    audit_service.record_update("financial_entry",11,{"amount_cents":200000,"description":"Escola"},{"amount_cents":200000,"description":"Escola 2026"}); rows=connection.execute("select field_name from audit_log where entity_id=11 order by id").fetchall(); assert [row[0] for row in rows]==["description"]

def test_delete_snapshot_survives_business_soft_delete(audit_service,connection):
    cursor=connection.execute("insert into financial_entry(competence_date,due_date,description,amount_cents,entry_type,status) values (?,?,?,?,?,?)",(date.today().isoformat(),date.today().isoformat(),"Condomínio",150000,"DESPESA","PENDENTE")); entry_id=cursor.lastrowid; before=dict(connection.execute("select * from financial_entry where id=?",(entry_id,)).fetchone()); audit_service.record_delete("financial_entry",entry_id,before); connection.execute("update financial_entry set deleted_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') where id=?",(entry_id,)); audit=connection.execute("select action,snapshot_json from audit_log where entity_id=?",(entry_id,)).fetchone(); assert audit[0]=="DELETE"; snapshot=json.loads(audit[1]); assert snapshot["description"]=="Condomínio"; assert snapshot["amount_cents"]==150000

def test_create_records_snapshot(audit_service,connection):
    audit_service.record_create("financial_entry",20,{"description":"Seguro","amount_cents":10000}); row=connection.execute("select action,snapshot_json from audit_log where entity_id=20").fetchone(); assert row[0]=="CREATE"; assert json.loads(row[1])=={"amount_cents":10000,"description":"Seguro"}
