CREATE TABLE IF NOT EXISTS local_user (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    entity TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('CREATE','UPDATE','DELETE')),
    field_name TEXT,
    old_value TEXT,
    new_value TEXT,
    snapshot_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity, entity_id, occurred_at);

CREATE TABLE IF NOT EXISTS recurrence_rule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    frequency TEXT NOT NULL DEFAULT 'MONTHLY' CHECK(frequency IN ('MONTHLY')),
    preferred_day INTEGER NOT NULL CHECK(preferred_day BETWEEN 1 AND 31),
    next_due_date TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS installment_group (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_description TEXT,
    total_installments INTEGER NOT NULL CHECK(total_installments > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS financial_entry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competence_date TEXT NOT NULL,
    due_date TEXT,
    settled_date TEXT,
    description TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0),
    entry_type TEXT NOT NULL CHECK(entry_type IN ('RECEITA','DESPESA','TRANSFERENCIA','INVESTIMENTO')),
    status TEXT NOT NULL CHECK(status IN ('PENDENTE','PAGO','RECEBIDO','ATRASADO','CANCELADO')),
    payment_method TEXT,
    notes TEXT,
    is_recurring INTEGER NOT NULL DEFAULT 0 CHECK(is_recurring IN (0,1)),
    installment_number INTEGER,
    installment_total INTEGER,
    recurrence_rule_id INTEGER REFERENCES recurrence_rule(id),
    installment_group_id INTEGER REFERENCES installment_group(id),
    beneficiary_id INTEGER,
    category_id INTEGER,
    subcategory_id INTEGER,
    cost_center_id INTEGER,
    bank_account_id INTEGER,
    card_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_financial_entry_due_date ON financial_entry(due_date) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_financial_entry_competence ON financial_entry(competence_date) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_financial_entry_status ON financial_entry(status) WHERE deleted_at IS NULL;
