CREATE TABLE IF NOT EXISTS points_transactions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    twitch_id  TEXT    NOT NULL,
    amount     INTEGER NOT NULL,
    reason     TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
