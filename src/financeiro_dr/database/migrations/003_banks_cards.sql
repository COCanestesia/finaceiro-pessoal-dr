CREATE TABLE IF NOT EXISTS bank_account (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL CHECK(length(trim(name)) > 0),
 institution TEXT,
 opening_balance_cents INTEGER NOT NULL DEFAULT 0,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS credit_card (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL CHECK(length(trim(name)) > 0),
 bank_account_id INTEGER REFERENCES bank_account(id),
 limit_cents INTEGER NOT NULL DEFAULT 0 CHECK(limit_cents>=0),
 closing_day INTEGER NOT NULL DEFAULT 1 CHECK(closing_day BETWEEN 1 AND 31),
 due_day INTEGER NOT NULL DEFAULT 10 CHECK(due_day BETWEEN 1 AND 31),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_financial_bank ON financial_entry(bank_account_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_financial_card ON financial_entry(card_id) WHERE deleted_at IS NULL;
