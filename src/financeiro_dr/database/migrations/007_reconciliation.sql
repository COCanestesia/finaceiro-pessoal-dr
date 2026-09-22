CREATE TABLE IF NOT EXISTS reconciliation_link (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 statement_row_id INTEGER NOT NULL REFERENCES statement_row(id),
 entry_id INTEGER REFERENCES financial_entry(id),
 status TEXT NOT NULL CHECK(status IN ('CONCILIADO','PENDENTE','DIVERGENTE')),
 score INTEGER,
 confirmed_at TEXT,
 note TEXT,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_recon_statement_active ON reconciliation_link(statement_row_id) WHERE status IN ('CONCILIADO','DIVERGENTE');
CREATE UNIQUE INDEX IF NOT EXISTS ux_recon_entry_conc ON reconciliation_link(entry_id) WHERE status='CONCILIADO' AND entry_id IS NOT NULL;
