from pathlib import Path
import sqlite3
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.people import PeopleService
from financeiro_dr.classification import ClassificationService
from financeiro_dr.budgets import BudgetService, classify_budget_percent

def db():
    c=sqlite3.connect(":memory:"); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); MigrationRunner().apply_all(c); return c

def test_people_classification_and_budget_scope():
    c=db(); p=PeopleService(c); cls=ClassificationService(c); b=BudgetService(c)
    pid=p.create("Pessoa X","Família")
    cat=cls.create_category("Saúde")
    sub=cls.create_subcategory(cat,"Medicamentos")
    cc=cls.create_cost_center("Casa 2")
    cls.validate_selection(cat,sub,cc)
    c.execute("INSERT INTO financial_entry(competence_date,description,amount_cents,entry_type,status,beneficiary_id,category_id,subcategory_id,cost_center_id) VALUES ('2026-09-01','Teste',9000,'DESPESA','PAGO',?,?,?,?)",(pid,cat,sub,cc)); c.commit()
    bid=b.create("2026-09",10000,category_id=cat)
    snap=b.snapshot(bid)
    assert snap.spent_cents==9000 and classify_budget_percent(snap.percent_used).level=="WARNING"
    p.set_active(pid,False)
    assert p.list_active()==[]

def test_subcategory_must_match_category():
    c=db(); s=ClassificationService(c); a=s.create_category("A"); other=s.create_category("B"); sub=s.create_subcategory(a,"x")
    try: s.validate_selection(other,sub,None)
    except ValueError as exc: assert "não pertence" in str(exc)
    else: raise AssertionError("deveria rejeitar")
