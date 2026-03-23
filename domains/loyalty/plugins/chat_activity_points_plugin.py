from core.base_plugin import BasePlugin

POINTS_PER_MESSAGE = 5
COOLDOWN_SECONDS = 60  # one award per user per minute


class ChatActivityPointsPlugin(BasePlugin):
    """
    Awards points for chat activity.

    Subscribes to chat.message.received. Awards POINTS_PER_MESSAGE points
    per user with a per-user cooldown to prevent spam farming.
    """

    def __init__(self, event_bus, db, state, logger):
        self.bus = event_bus
        self.db = db
        self.state = state
        self.logger = logger

    async def on_boot(self):
        await self.bus.subscribe("chat.message.received", self._on_message)

    async def _on_message(self, msg: dict):
        twitch_id = msg.get("user_id", "")
        display_name = msg.get("display_name", "")
        if not twitch_id:
            return

        cooldown_key = f"activity_cooldown:{twitch_id}"
        if self.state.get(cooldown_key, namespace="loyalty"):
            return

        self.state.set(cooldown_key, True, namespace="loyalty")
        import asyncio
        asyncio.get_event_loop().call_later(
            COOLDOWN_SECONDS,
            lambda: self.state.delete(cooldown_key, namespace="loyalty"),
        )

        try:
            existing = await self.db.query_one(
                "SELECT id FROM viewer_points WHERE twitch_id=$1", [twitch_id]
            )
            if existing:
                await self.db.execute(
                    """UPDATE viewer_points
                       SET points=points+$1, total_earned=total_earned+$1,
                           display_name=$2, updated_at=datetime('now')
                       WHERE twitch_id=$3""",
                    [POINTS_PER_MESSAGE, display_name, twitch_id],
                )
            else:
                await self.db.execute(
                    """INSERT INTO viewer_points (twitch_id, display_name, points, total_earned)
                       VALUES ($1, $2, $3, $3)""",
                    [twitch_id, display_name, POINTS_PER_MESSAGE],
                )
            await self.db.execute(
                "INSERT INTO points_transactions (twitch_id, amount, reason) VALUES ($1,$2,$3)",
                [twitch_id, POINTS_PER_MESSAGE, "chat_activity"],
            )
        except Exception as e:
            self.logger.error(f"[ChatActivityPoints] {e}")
