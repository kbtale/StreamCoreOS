CREATE TABLE IF NOT EXISTS stream_sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    twitch_stream_id TEXT,
    started_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    ended_at         TEXT,
    title            TEXT,
    game_name        TEXT,
    peak_viewers     INTEGER NOT NULL DEFAULT 0
);
