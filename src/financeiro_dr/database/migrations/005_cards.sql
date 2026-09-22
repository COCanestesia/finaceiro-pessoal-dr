CREATE TABLE IF NOT EXISTS credit_card (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 issuer TEXT NOT NULL,
 holder TEXT NOT NULL,
 name TEXT,
 limit_cents INTEGER NOT NULL CHECK(limit_cents>=0),
 closing_day INTEGER NOT NULL CHECK(closing_day BETWEEN 1 AND 31),
 due_day INTEGER NOT NULL CHECK(due_day BETWEEN 1 AND 31),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS card_purchase (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 card_id INTEGER NOT NULL REFERENCES credit_card(id),
 purchase_date TEXT NOT NULL,
 description TEXT NOT NULL,
 total_cents INTEGER NOT NULL CHECK(total_cents>0),
 installments INTEGER NOT NULL DEFAULT 1 CHECK(installments>0),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS card_installment (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 purchase_id INTEGER NOT NULL REFERENCES card_purchase(id),
 installment_number INTEGER NOT NULL,
 amount_cents INTEGER NOT NULL,
 invoice_year INTEGER NOT NULL,
 invoice_month INTEGER NOT NULL,
 entry_id INTEGER NOT NULL REFERENCES financial_entry(id),
 paid INTEGER NOT NULL DEFAULT 0 CHECK(paid IN (0,1)),
 UNIQUE(purchase_id,installment_number)
);
CREATE TABLE IF NOT EXISTS card_invoice_payment (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 card_id INTEGER NOT NULL REFERENCES credit_card(id),
 invoice_year INTEGER NOT NULL,
 invoice_month INTEGER NOT NULL,
 amount_cents INTEGER NOT NULL,
 paid_at TEXT NOT NULL,
 UNIQUE(card_id,invoice_year,invoice_month)
);
