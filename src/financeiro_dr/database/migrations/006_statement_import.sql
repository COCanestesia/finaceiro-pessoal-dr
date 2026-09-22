CREATE TABLE IF NOT EXISTS statement_import (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 account_id INTEGER NOT NULL REFERENCES bank_account(id),
 source_name TEXT NOT NULL,
 imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 row_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS statement_row (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 import_id INTEGER NOT NULL REFERENCES statement_import(id),
 account_id INTEGER NOT NULL REFERENCES bank_account(id),
 external_id TEXT,
 posted_date TEXT NOT NULL,
 amount_cents INTEGER NOT NULL,
 description TEXT NOT NULL,
 raw_hash TEXT NOT NULL,
 ignored INTEGER NOT NULL DEFAULT 0 CHECK(ignored IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 UNIQUE(account_id,raw_hash)
);
