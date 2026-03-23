CREATE TABLE IF NOT EXISTS viewer_points (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    twitch_id    TEXT    NOT NULL UNIQUE,
    display_name TEXT    NOT NULL,
    points       INTEGER NOT NULL DEFAULT 0,
    total_earned INTEGER NOT NULL DEFAULT 0,
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
