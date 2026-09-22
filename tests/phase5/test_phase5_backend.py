from datetime import date
from pathlib import Path
import sqlite3
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.service import FinancialService
from financeiro_dr.reports import ReportQueryService,ReportFilters,export_xlsx,export_pdf
from financeiro_dr.backup import BackupService,RestoreService

def dbfile(tmp_path):
 p=tmp_path/'db.sqlite';c=sqlite3.connect(p);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');MigrationRunner().apply_all(c);return p,c

def test_reports_and_exports(tmp_path):
 p,c=dbfile(tmp_path);f=FinancialService(c);f.create_entry(CreateEntry('Conta',12345,'DESPESA','PAGO',date(2026,9,1),expense_nature='FIXA'));r=ReportQueryService(c).expenses(ReportFilters(date(2026,9,1),date(2026,9,30)));assert r.total_cents==12345 and len(r.detail_entry_ids)==1;assert export_xlsx(r,tmp_path/'r.xlsx').exists();assert export_pdf(r,tmp_path/'r.pdf').exists()

def test_backup_restore(tmp_path):
 p,c=dbfile(tmp_path);docs=tmp_path/'docs';docs.mkdir();(docs/'x.txt').write_text('x');dest=tmp_path/'backups';b=BackupService(c,p,docs);result=b.create(dest);assert result.path.exists();v=RestoreService(c,p,docs).validate(result.path);assert v.ok
