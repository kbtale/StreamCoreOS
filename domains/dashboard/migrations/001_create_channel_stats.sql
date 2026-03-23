CREATE TABLE IF NOT EXISTS channel_stats (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    viewer_count   INTEGER NOT NULL DEFAULT 0,
    follower_count INTEGER NOT NULL DEFAULT 0
);
