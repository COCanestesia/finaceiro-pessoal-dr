from datetime import date
from pathlib import Path
import sqlite3
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.assets import AssetService
from financeiro_dr.investments import InvestmentService
from financeiro_dr.documents import DocumentService,DocumentFilters

def db():
 c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');MigrationRunner().apply_all(c);return c

def test_assets_investments_documents(tmp_path):
 c=db(); a=AssetService(c); aid=a.create('IMOVEL','Casa',date(2020,1,1),500000,700000,None); a.update_estimated_value(aid,750000); row=c.execute('SELECT * FROM asset WHERE id=?',(aid,)).fetchone(); assert row['acquisition_value_cents']==500000 and row['estimated_value_cents']==750000
 i=InvestmentService(c); iid=i.create('Banco','Aplicação','CDB'); i.add_movement(iid,'APORTE',100000,date(2026,1,1)); i.add_movement(iid,'RENDIMENTO',5000,date(2026,1,31)); i.add_movement(iid,'RESGATE',20000,date(2026,2,1)); s=i.summary(); assert s.balance_cents==85000 and s.return_cents==5000
 f=tmp_path/'recibo.pdf';f.write_bytes(b'A');d=DocumentService(c,tmp_path/'docs');first=d.attach(f,'RECIBO',asset_id=aid);f.write_bytes(b'B');second=d.attach(f,'RECIBO',asset_id=aid);assert d.resolve_path(first)!=d.resolve_path(second); assert len(d.search(DocumentFilters(asset_id=aid)))==2
