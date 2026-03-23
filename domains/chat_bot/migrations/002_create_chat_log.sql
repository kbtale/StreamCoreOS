CREATE TABLE IF NOT EXISTS chat_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    channel      TEXT    NOT NULL,
    user_id      TEXT    NOT NULL,
    display_name TEXT    NOT NULL,
    message      TEXT    NOT NULL,
    is_command   INTEGER NOT NULL DEFAULT 0,
    timestamp    TEXT    NOT NULL
);
