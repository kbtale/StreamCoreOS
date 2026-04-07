from core.base_plugin import BasePlugin

class EchoReminderPlugin(BasePlugin):
    """
    Skeleton for the !echo [time] [message] command.
    """

    def __init__(self, event_bus, logger):
        self.bus = event_bus
        self.logger = logger

    async def on_boot(self):
        # register for the chat command
        await self.bus.subscribe("chat.command.received", self._on_command)

    async def _on_command(self, data: dict):
        if data.get("command") != "!echo":
            return
        
        self.logger.info(f"[Echo] Command received from @{data.get('display_name')}")
