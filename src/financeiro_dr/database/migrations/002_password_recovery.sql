CREATE TABLE IF NOT EXISTS password_recovery (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    token_hash TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
