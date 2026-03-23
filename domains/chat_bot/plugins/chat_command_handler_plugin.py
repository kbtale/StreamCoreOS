from core.base_plugin import BasePlugin


class ChatCommandHandlerPlugin(BasePlugin):
    """
    Handles chat commands stored in the DB.

    Subscribes to chat.command.received. For each command:
      1. Looks up the command in DB by name.
      2. Checks per-user cooldown via the state tool.
      3. If valid, sends the response to chat (supports {user} template).
      4. Publishes chat.command.executed.
    """

    def __init__(self, twitch, event_bus, db, state, logger):
        self.twitch = twitch
        self.bus = event_bus
        self.db = db
        self.state = state
        self.logger = logger

    async def on_boot(self):
        await self.bus.subscribe("chat.command.received", self._handle)

    async def _handle(self, data: dict):
        command_name = data.get("command", "").lower()
        user_id = data.get("user_id", "")
        display_name = data.get("display_name", "")
        channel = data.get("channel", "")

        try:
            cmd = await self.db.query_one(
                "SELECT * FROM chat_commands WHERE name=$1 AND enabled=1",
                [command_name],
            )
            if not cmd:
                return

            # Check cooldown per user
            cooldown_key = f"cmd_cooldown:{command_name}:{user_id}"
            if self.state.get(cooldown_key, namespace="chat_bot"):
                return

            # Set cooldown
            self.state.set(cooldown_key, True, namespace="chat_bot")
            # Schedule cooldown expiry (best effort via asyncio)
            import asyncio
            asyncio.get_event_loop().call_later(
                cmd["cooldown_s"],
                lambda: self.state.delete(cooldown_key, namespace="chat_bot"),
            )

            response = cmd["response"].replace("{user}", display_name)
            await self.twitch.send_message(channel, response)
            await self.bus.publish("chat.command.executed", {
                "command": command_name,
                "user_id": user_id,
                "display_name": display_name,
                "channel": channel,
            })
        except Exception as e:
            self.logger.error(f"[CommandHandler] Error handling {command_name}: {e}")
