CREATE TABLE IF NOT EXISTS mod_rules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    type       TEXT    NOT NULL,
    value      TEXT,
    action     TEXT    NOT NULL DEFAULT 'timeout',
    duration_s INTEGER,
    enabled    INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
