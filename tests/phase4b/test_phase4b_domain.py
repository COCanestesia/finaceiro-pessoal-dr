from datetime import date
import sqlite3
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.database.health import DatabaseHealth
from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.service import FinancialService
from financeiro_dr.income_sources import IncomeSourceService
from financeiro_dr.core.financeiro.dashboard_charts import DashboardChartService

def db():
 c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');MigrationRunner().apply_all(c);return c

def test_reporting_classification_and_health():
 c=db(); assert DatabaseHealth.check(c).ok
 source=IncomeSourceService(c).list_active()[0]
 finance=FinancialService(c); finance.create_entry(CreateEntry('Aluguel',1000,'DESPESA','PAGO',date(2026,9,1),expense_nature='FIXA')); finance.create_entry(CreateEntry('Receita',5000,'RECEITA','RECEBIDO',date(2026,9,1),income_source_id=source.id))
 data=DashboardChartService(c).cash_flow_6_months(date(2026,9,1)); assert data.points[-1].value_cents==4000
