CREATE TABLE IF NOT EXISTS backup_log (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 destination TEXT NOT NULL,
 reason TEXT NOT NULL CHECK(reason IN ('AUTO','MANUAL','PRE_RESTORE')),
 status TEXT NOT NULL CHECK(status IN ('SUCCESS','ERROR')),
 message TEXT,
 file_name TEXT
);
