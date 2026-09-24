CREATE TABLE IF NOT EXISTS initial_seed_batch (
    seed_id TEXT PRIMARY KEY,
    source_label TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    expected_count INTEGER NOT NULL CHECK(expected_count >= 0),
    applied_count INTEGER NOT NULL CHECK(applied_count >= 0),
    warning_count INTEGER NOT NULL CHECK(warning_count >= 0),
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS initial_seed_record (
    seed_id TEXT NOT NULL REFERENCES initial_seed_batch(seed_id),
    source_row INTEGER NOT NULL,
    record_hash TEXT NOT NULL,
    financial_entry_id INTEGER NOT NULL REFERENCES financial_entry(id),
    action TEXT NOT NULL CHECK(action IN ('INSERTED','REUSED_EXISTING')),
    warning_code TEXT,
    PRIMARY KEY(seed_id, source_row)
);

CREATE INDEX IF NOT EXISTS idx_initial_seed_record_entry
ON initial_seed_record(financial_entry_id);
