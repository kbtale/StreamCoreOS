import asyncio
import httpx
from core.base_plugin import BasePlugin

# AI Configuration (Aligned with TailwindModerationIAPlugin)
AI_URL = "http://192.168.1.80:8080/v1/chat/completions"
AI_MODEL = "LFM2-24B-A2B-Q4_K_M"
MAX_RESPONSE_CHARS = 450  # Twitch chat limit is 500


class IAChatPlugin(BasePlugin):
    """
    Responds to !ia <question> in Twitch chat using a local LLM server.

    Usage in chat:  !ia ¿cuántos planetas tiene el sistema solar?
    The bot replies directly in chat with the AI's answer (truncated to fit Twitch limit).

    Per-user cooldown of 120 s to prevent abuse.
    """

    COOLDOWN_S = 120

    def __init__(self, twitch, event_bus, state, logger):
        self.twitch = twitch
        self.bus = event_bus
        self.state = state
        self.logger = logger

    async def on_boot(self):
        await self.bus.subscribe("chat.command.received", self._handle)

    async def _handle(self, data: dict):
        command = data.get("command", "").lower()
        if command != "!ia":
            return

        question = data.get("args", "").strip()
        if not question:
            await self.twitch.send_message(
                data["channel"],
                f"@{data['display_name']} Escribe tu pregunta después de !ia 😊",
            )
            return

        user_id = data.get("user_id", "")
        cooldown_key = f"ia_cooldown:{user_id}"
        if self.state.get(cooldown_key, namespace="ia_chat"):
            return

        self.state.set(cooldown_key, True, namespace="ia_chat")
        asyncio.get_event_loop().call_later(
            self.COOLDOWN_S,
            lambda: self.state.delete(cooldown_key, namespace="ia_chat"),
        )

        await self.twitch.send_message(
            data["channel"],
            f"@{data['display_name']} Pensando... 🤔",
        )

        try:
            answer = await self._query_ai(question)
            reply = f"@{data['display_name']} {answer}"
            if len(reply) > MAX_RESPONSE_CHARS:
                reply = reply[: MAX_RESPONSE_CHARS - 1] + "…"
            await self.twitch.send_message(data["channel"], reply)
        except Exception as e:
            self.logger.error(f"[IAChatPlugin] AI error: {e}")
            await self.twitch.send_message(
                data["channel"],
                f"@{data['display_name']} No pude obtener respuesta de la IA. Inténtalo más tarde.",
            )

    async def _query_ai(self, prompt: str) -> str:
        payload = {
            "model": AI_MODEL,
            "messages": [
                {
                    "role": "system", 
                    "content": "Eres un asistente de chat de Twitch servicial y conciso. Responde siempre en español y en menos de 40 palabras."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 200
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(AI_URL, json=payload)
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"].strip()
