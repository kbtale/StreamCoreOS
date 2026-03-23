CREATE TABLE IF NOT EXISTS mod_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    twitch_id    TEXT    NOT NULL,
    display_name TEXT    NOT NULL,
    action       TEXT    NOT NULL,
    reason       TEXT    NOT NULL,
    rule_id      INTEGER,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
