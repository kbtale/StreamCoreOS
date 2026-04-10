import json
from core.base_plugin import BasePlugin


class RestoreAIConfigPlugin(BasePlugin):
    """
    Reads the saved AI config from DB on boot and pushes it into AITool.
    This is the only bridge DB → AITool, keeping the tool DB-free.

    extra_headers and extra_payload are stored as JSON strings in SQLite
    and deserialized here before passing to load_config().
    """

    def __init__(self, db, ai, logger):
        self.db = db
        self.ai = ai
        self.logger = logger

    async def on_boot(self):
        try:
            row = await self.db.query_one("SELECT * FROM ai_config WHERE id = 1")
            if row:
                config = dict(row)
                # Deserialize JSON string fields back to dicts
                for field in ("extra_headers", "extra_payload"):
                    val = config.get(field)
                    if isinstance(val, str):
                        try:
                            config[field] = json.loads(val)
                        except Exception:
                            config[field] = {}
                self.ai.load_config(config)
                self.logger.info("[AIConfig] Config restored from DB.")
            else:
                self.logger.info("[AIConfig] No saved config found — AI tool unconfigured.")
        except Exception:
            # Normal on first boot — table doesn't exist until migrations run.
            self.logger.info("[AIConfig] No config to restore (first boot or table pending).")
