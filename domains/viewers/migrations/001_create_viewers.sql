CREATE TABLE IF NOT EXISTS viewers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    twitch_id     TEXT    UNIQUE NOT NULL,
    login         TEXT    NOT NULL,
    display_name  TEXT    NOT NULL,
    points        INTEGER NOT NULL DEFAULT 0,
    total_earned  INTEGER NOT NULL DEFAULT 0,
    is_regular    INTEGER NOT NULL DEFAULT 0,
    first_seen    TEXT    NOT NULL DEFAULT (datetime('now')),
    last_seen     TEXT    NOT NULL DEFAULT (datetime('now'))
);
