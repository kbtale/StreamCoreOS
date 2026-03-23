from core.base_plugin import BasePlugin

# Points awarded per event type
POINTS_TABLE = {
    "channel.follow": 100,
    "channel.subscribe": 500,
    "channel.subscription.message": 300,   # resub
    "channel.subscription.gift": 200,       # per gift (× total)
    "channel.cheer": 1,                     # per bit (× bits)
    "channel.raid": 10,                     # per viewer (× viewers)
}


class AwardPointsPlugin(BasePlugin):
    """
    Awards loyalty points to viewers based on Twitch events.

    Registers for the same events as chat_auto_response. Deduplication
    in TwitchTool ensures only one Twitch subscription is created per event.
    """

    def __init__(self, twitch, event_bus, db, logger):
        self.twitch = twitch
        self.bus = event_bus
        self.db = db
        self.logger = logger

    async def on_boot(self):
        self.twitch.register(
            "channel.follow", "2",
            scopes=["moderator:read:followers"],
            condition={
                "broadcaster_user_id": "{broadcaster_id}",
                "moderator_user_id": "{broadcaster_id}",
            },
        )
        self.twitch.register("channel.subscribe", "1", scopes=["channel:read:subscriptions"])
        self.twitch.register("channel.subscription.message", "1", scopes=["channel:read:subscriptions"])
        self.twitch.register("channel.subscription.gift", "1", scopes=["channel:read:subscriptions"])
        self.twitch.register("channel.cheer", "1", scopes=["bits:read"])
        self.twitch.register(
            "channel.raid", "1", scopes=[],
            condition={"to_broadcaster_user_id": "{broadcaster_id}"},
        )

        self.twitch.on_event("channel.follow", self._on_follow)
        self.twitch.on_event("channel.subscribe", self._on_subscribe)
        self.twitch.on_event("channel.subscription.message", self._on_resub)
        self.twitch.on_event("channel.subscription.gift", self._on_gift)
        self.twitch.on_event("channel.cheer", self._on_cheer)
        self.twitch.on_event("channel.raid", self._on_raid)

    async def _award(self, twitch_id: str, display_name: str, amount: int, reason: str):
        if amount <= 0:
            return
        try:
            async with self.db.transaction() as tx:
                existing = await tx.query_one(
                    "SELECT id FROM viewer_points WHERE twitch_id=$1", [twitch_id]
                )
                if existing:
                    await tx.execute(
                        """UPDATE viewer_points
                           SET points=points+$1, total_earned=total_earned+$1,
                               display_name=$2, updated_at=datetime('now')
                           WHERE twitch_id=$3""",
                        [amount, display_name, twitch_id],
                    )
                else:
                    await tx.execute(
                        """INSERT INTO viewer_points (twitch_id, display_name, points, total_earned)
                           VALUES ($1, $2, $3, $3)""",
                        [twitch_id, display_name, amount],
                    )
                await tx.execute(
                    "INSERT INTO points_transactions (twitch_id, amount, reason) VALUES ($1,$2,$3)",
                    [twitch_id, amount, reason],
                )
            await self.bus.publish("loyalty.points.awarded", {
                "twitch_id": twitch_id, "display_name": display_name,
                "amount": amount, "reason": reason,
            })
        except Exception as e:
            self.logger.error(f"[AwardPoints] Failed to award {amount} pts to {twitch_id}: {e}")

    async def _on_follow(self, event: dict):
        await self._award(
            event.get("user_id", ""), event.get("user_name", ""),
            POINTS_TABLE["channel.follow"], "follow",
        )

    async def _on_subscribe(self, event: dict):
        await self._award(
            event.get("user_id", ""), event.get("user_name", ""),
            POINTS_TABLE["channel.subscribe"], "subscribe",
        )

    async def _on_resub(self, event: dict):
        await self._award(
            event.get("user_id", ""), event.get("user_name", ""),
            POINTS_TABLE["channel.subscription.message"], "resub",
        )

    async def _on_gift(self, event: dict):
        total = event.get("total", 1)
        amount = POINTS_TABLE["channel.subscription.gift"] * total
        await self._award(
            event.get("user_id", ""), event.get("user_name", "Anonymous"),
            amount, f"gift_sub×{total}",
        )

    async def _on_cheer(self, event: dict):
        bits = event.get("bits", 0)
        amount = POINTS_TABLE["channel.cheer"] * bits
        await self._award(
            event.get("user_id", ""), event.get("user_name", ""),
            amount, f"cheer_{bits}_bits",
        )

    async def _on_raid(self, event: dict):
        viewers = event.get("viewers", 0)
        amount = POINTS_TABLE["channel.raid"] * viewers
        await self._award(
            event.get("from_broadcaster_user_id", ""),
            event.get("from_broadcaster_user_name", ""),
            amount, f"raid_{viewers}_viewers",
        )
