CREATE TABLE IF NOT EXISTS twitch_tokens (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    twitch_id     TEXT    NOT NULL UNIQUE,
    login         TEXT    NOT NULL,
    display_name  TEXT    NOT NULL,
    access_token  TEXT    NOT NULL,
    refresh_token TEXT    NOT NULL,
    scopes        TEXT    NOT NULL DEFAULT '[]',
    expires_at    TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
