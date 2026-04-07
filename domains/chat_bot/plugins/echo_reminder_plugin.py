import re
from typing import Optional
from core.base_plugin import BasePlugin

class EchoReminderPlugin(BasePlugin):
    """
    Skeleton for the !echo [time] [message] command.
    """

    def __init__(self, event_bus, logger):
        self.bus = event_bus
        self.logger = logger
        self._duration_regex = re.compile(r"^(\d+)([smh])$")

    async def on_boot(self):
        # Register for the chat command
        await self.bus.subscribe("chat.command.received", self._on_command)

    async def _on_command(self, data: dict):
        if data.get("command") != "!echo":
            return
        
        # Get the full arguments string and split it
        args_str = data.get("args", "")
        if not args_str:
            return
            
        parts = args_str.split(maxsplit=1)
        time_str = parts[0]
        
        # Parse duration
        seconds = self._parse_duration(time_str)
        if seconds is None:
            self.logger.warning(f"[Echo] Invalid duration: {time_str}")
            return
            
        self.logger.info(f"[Echo] Parsed duration: {seconds}s from @{data.get('display_name')}")

    def _parse_duration(self, duration_str: str) -> Optional[int]:
        match = self._duration_regex.match(duration_str.lower())
        if not match:
            return None
        
        value, unit = match.groups()
        value = int(value)
        
        if unit == "s": return value
        if unit == "m": return value * 60
        if unit == "h": return value * 3600
        return None
