CREATE TABLE IF NOT EXISTS bank_account (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 institution TEXT NOT NULL,
 name TEXT NOT NULL,
 opening_balance_cents INTEGER NOT NULL DEFAULT 0,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS internal_transfer (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 source_account_id INTEGER NOT NULL REFERENCES bank_account(id),
 target_account_id INTEGER NOT NULL REFERENCES bank_account(id),
 amount_cents INTEGER NOT NULL CHECK(amount_cents>0),
 transfer_date TEXT NOT NULL,
 description TEXT NOT NULL,
 source_entry_id INTEGER REFERENCES financial_entry(id),
 target_entry_id INTEGER REFERENCES financial_entry(id),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
