CREATE TABLE IF NOT EXISTS investment_account (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 institution TEXT NOT NULL,
 account_name TEXT NOT NULL,
 investment_type TEXT NOT NULL,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS investment_movement (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 investment_id INTEGER NOT NULL REFERENCES investment_account(id),
 movement_type TEXT NOT NULL CHECK(movement_type IN ('APORTE','RESGATE','RENDIMENTO','AJUSTE')),
 amount_cents INTEGER NOT NULL,
 movement_date TEXT NOT NULL,
 notes TEXT,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_investment_movement_date ON investment_movement(investment_id,movement_date);
