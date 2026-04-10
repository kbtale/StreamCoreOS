ALTER TABLE ai_config ADD COLUMN timeout_s      INTEGER NOT NULL DEFAULT 120;
ALTER TABLE ai_config ADD COLUMN extra_headers  TEXT    NOT NULL DEFAULT '{}';
ALTER TABLE ai_config ADD COLUMN extra_payload  TEXT    NOT NULL DEFAULT '{}';
