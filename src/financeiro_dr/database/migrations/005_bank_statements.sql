CREATE TABLE IF NOT EXISTS bank_statement_line (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 account_id INTEGER NOT NULL REFERENCES bank_account(id),
 posted_date TEXT NOT NULL,
 description TEXT NOT NULL,
 amount_cents INTEGER NOT NULL CHECK(amount_cents <> 0),
 fingerprint TEXT NOT NULL,
 matched_entry_id INTEGER REFERENCES financial_entry(id),
 imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(account_id, fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_bank_statement_account_date ON bank_statement_line(account_id,posted_date);
