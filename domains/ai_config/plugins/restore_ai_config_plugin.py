from core.base_plugin import BasePlugin


class RestoreAIConfigPlugin(BasePlugin):
    """
    Reads the saved AI config from DB on boot and pushes it into AITool.
    This is the only place that bridges DB → AITool, keeping the tool DB-free.
    """

    def __init__(self, db, ai, logger):
        self.db = db
        self.ai = ai
        self.logger = logger

    async def on_boot(self):
        try:
            row = await self.db.query_one("SELECT * FROM ai_config WHERE id = 1")
            if row:
                self.ai.load_config(dict(row))
                self.logger.info("[AIConfig] Config restored from DB.")
            else:
                self.logger.info("[AIConfig] No saved config found — AI tool unconfigured.")
        except Exception:
            # Normal on first boot — table doesn't exist until migrations run.
            self.logger.info("[AIConfig] No config to restore (first boot or table pending).")
