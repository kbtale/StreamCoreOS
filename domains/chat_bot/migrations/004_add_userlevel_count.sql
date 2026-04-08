ALTER TABLE chat_commands ADD COLUMN userlevel TEXT NOT NULL DEFAULT 'everyone';
ALTER TABLE chat_commands ADD COLUMN use_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE chat_commands ADD COLUMN global_cooldown_s INTEGER NOT NULL DEFAULT 0;
