CREATE TABLE IF NOT EXISTS card_statement_import (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 card_id INTEGER NOT NULL REFERENCES credit_card(id),
 source_name TEXT NOT NULL,
 imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 row_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS card_statement_row (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 import_id INTEGER NOT NULL REFERENCES card_statement_import(id),
 card_id INTEGER NOT NULL REFERENCES credit_card(id),
 external_id TEXT,
 posted_date TEXT NOT NULL,
 amount_cents INTEGER NOT NULL,
 description TEXT NOT NULL,
 raw_hash TEXT NOT NULL,
 ignored INTEGER NOT NULL DEFAULT 0 CHECK(ignored IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 UNIQUE(card_id,raw_hash)
);
CREATE TABLE IF NOT EXISTS card_reconciliation_link (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 statement_row_id INTEGER NOT NULL REFERENCES card_statement_row(id),
 purchase_id INTEGER REFERENCES card_purchase(id),
 status TEXT NOT NULL CHECK(status IN ('CONCILIADO','PENDENTE','DIVERGENTE')),
 score INTEGER,
 confirmed_at TEXT,
 note TEXT,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_card_recon_row_active ON card_reconciliation_link(statement_row_id) WHERE status IN ('CONCILIADO','DIVERGENTE');
CREATE UNIQUE INDEX IF NOT EXISTS ux_card_recon_purchase ON card_reconciliation_link(purchase_id) WHERE status='CONCILIADO' AND purchase_id IS NOT NULL;
