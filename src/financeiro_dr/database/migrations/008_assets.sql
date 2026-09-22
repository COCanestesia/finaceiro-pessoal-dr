CREATE TABLE IF NOT EXISTS asset (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 asset_type TEXT NOT NULL CHECK(asset_type IN ('IMOVEL','VEICULO','TERRENO','OUTRO')),
 description TEXT NOT NULL,
 acquisition_date TEXT,
 acquisition_value_cents INTEGER NOT NULL DEFAULT 0 CHECK(acquisition_value_cents>=0),
 estimated_value_cents INTEGER NOT NULL DEFAULT 0 CHECK(estimated_value_cents>=0),
 notes TEXT,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
ALTER TABLE financial_entry ADD COLUMN asset_id INTEGER REFERENCES asset(id);
