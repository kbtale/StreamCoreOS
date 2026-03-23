CREATE TABLE IF NOT EXISTS chat_commands (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    response    TEXT    NOT NULL,
    cooldown_s  INTEGER NOT NULL DEFAULT 30,
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
