from datetime import date
import sqlite3
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.service import FinancialService
from financeiro_dr.people import PeopleService
from financeiro_dr.classification import ClassificationService
from financeiro_dr.budgets import BudgetService
from financeiro_dr.reports import ReportFilters,ReportQueryService

def db():
 c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');MigrationRunner().apply_all(c);return c

def test_grouped_reports_keep_drilldown_and_budget_report():
 c=db();p=PeopleService(c).create('Filho');cls=ClassificationService(c);cat=cls.create_category('Educação');FinancialService(c).create_entry(CreateEntry('Escola',10000,'DESPESA','PAGO',date(2026,9,1),beneficiary_id=p,category_id=cat,expense_nature='FIXA'));BudgetService(c).create('2026-09',15000,person_id=p,category_id=cat);f=ReportFilters(date(2026,9,1),date(2026,9,30));svc=ReportQueryService(c);by_person=svc.expenses_by_person(f);budget=svc.budget_vs_actual(f);assert by_person.total_cents==10000 and len(by_person.detail_entry_ids)==1;assert budget.total_cents==10000 and budget.rows[0][4]==150.0

def test_report_service_exposes_all_spec_reports():
 c=db();svc=ReportQueryService(c);names={'expenses','income','expenses_by_person','expenses_by_category','expenses_by_subcategory','expenses_by_cost_center','expenses_by_bank','expenses_by_card','expenses_by_status','fixed_vs_variable','income_by_source','payables','receivables','budget_vs_actual','reconciliation','card_invoices','cash_flow','monthly_evolution','assets','investments','net_worth'};assert all(callable(getattr(svc,n,None)) for n in names)
