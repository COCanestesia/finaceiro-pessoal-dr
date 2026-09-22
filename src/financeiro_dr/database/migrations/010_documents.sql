CREATE TABLE IF NOT EXISTS document (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 original_name TEXT NOT NULL,
 stored_name TEXT,
 sha256 TEXT NOT NULL,
 size_bytes INTEGER NOT NULL,
 mime_type TEXT,
 document_type TEXT NOT NULL,
 relative_path TEXT,
 entry_id INTEGER REFERENCES financial_entry(id),
 asset_id INTEGER REFERENCES asset(id),
 person_id INTEGER REFERENCES person(id),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_document_links ON document(entry_id,asset_id,person_id);
