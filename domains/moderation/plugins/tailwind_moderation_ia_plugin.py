import httpx
import asyncio
from core.base_plugin import BasePlugin

# AI Configuration
AI_URL = "http://192.168.1.80:8080/v1/chat/completions"
AI_MODEL = "LFM2-24B-A2B-Q4_K_M"

class TailwindModerationIAPlugin(BasePlugin):
    """
    Advanced AI moderation plugin that detects any form of 'tailwind' mention
    (obfuscated, morse, leetspeak, etc.) using a local LLM and deletes the message.
    """

    def __init__(self, twitch, event_bus, db, state, logger):
        self.twitch = twitch
        self.bus = event_bus
        self.db = db
        self.state = state
        self.logger = logger
        self.cooldown_s = 15

    async def on_boot(self):
        # Ensure we have the necessary scopes
        self.twitch.require_scopes(["moderator:manage:chat_messages"])
        # Listen for incoming chat messages
        await self.bus.subscribe("chat.message.received", self._on_message)
        self.logger.info(f"[AI-Mod] Tailwind detection active using model {AI_MODEL}")

    async def _on_message(self, msg: dict):
        # Never moderate broadcaster or mods
        if msg.get("is_broadcaster") or msg.get("is_mod"):
            return

        message = msg.get("message", "").strip()
        if not message:
            return

        user_id = msg.get("user_id", "")
        message_id = msg.get("message_id", "")
        display_name = msg.get("display_name", "")

        # Per-user cooldown to not overload the local AI
        cooldown_key = f"ai_mod_cooldown:{user_id}"
        if self.state.get(cooldown_key, namespace="moderation"):
            return

        # Start evaluation
        try:
            is_bad = await self._check_with_ai(message)
            
            if is_bad:
                await self._enforce_delete(msg)
                self.logger.warning(f"[AI-Mod] Deleted message from {display_name}: {message}")
            
            # Set cooldown
            self.state.set(cooldown_key, True, namespace="moderation")
            asyncio.get_event_loop().call_later(
                self.cooldown_s,
                lambda: self.state.delete(cooldown_key, namespace="moderation")
            )
            
        except Exception as e:
            self.logger.error(f"[AI-Mod] Error evaluating message: {e}")

    async def _check_with_ai(self, text: str) -> bool:
        """
        Queries the local AI to detect if the text contains 'tailwind' in ANY form.
        Returns True if detected.
        """
        system_prompt = (
            "You are a precise chat moderator. Your ONLY goal is to detect if a message is an attempt to say 'tailwind'.\n"
            "ALLOWED WORDS (Do NOT flag these): 'linkedin', 'terminal', 'tainy', 'tain', 'tabien', 'taiwan', 'tail', 'tall', 'tell', 'wind', 'window'.\n"
            "FLAG THESE (Obfuscations): \n"
            "- Morse code for tailwind\n"
            "- Base64 for tailwind (dGFpbHdpbmQ=)\n"
            "- Leetspeak (T41lw1nd), separations (t-a-i-l-w-i-n-d), or phonetic hacks.\n"
            "- Clear translations like 'viento de cola'.\n\n"
            "If the message is NOT clearly about 'tailwind', you MUST respond with 'FALSE'.\n"
            "Respond ONLY with 'TRUE' or 'FALSE'. No explanations."
        )

        payload = {
            "model": AI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Message: {text}"}
            ],
            "temperature": 0.0,
            "max_tokens": 5
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(AI_URL, json=payload)
                resp.raise_for_status()
                result = resp.json()
                content = result["choices"][0]["message"]["content"].strip().upper()
                # Strict check: must be exactly TRUE
                return "TRUE" == content
        except Exception as e:
            self.logger.error(f"[AI-Mod] AI API Failure: {e}")
            return False

    async def _enforce_delete(self, msg: dict):
        session = self.twitch.get_session()
        if not session:
            return

        broadcaster_id = session["broadcaster_id"]
        access_token = session["access_token"]
        message_id = msg.get("message_id")
        user_id = msg.get("user_id")
        display_name = msg.get("display_name")
        reason = "AI-Mod: Detected 'tailwind' mention (Restricted Word)"

        if not message_id:
            return

        try:
            # Delete message via Helix
            params = {
                "broadcaster_id": broadcaster_id,
                "moderator_id": broadcaster_id,
                "message_id": message_id
            }
            await self.twitch.delete("/moderation/chat", params=params, user_token=access_token)

            # Log to DB
            await self.db.execute(
                """INSERT INTO mod_log (twitch_id, display_name, action, reason, rule_id)
                   VALUES ($1, $2, $3, $4, $5)""",
                [user_id, display_name, "delete", reason, 0] # 0 = AI Rule
            )
            
            # Notify bus
            await self.bus.publish("moderation.action.taken", {
                "twitch_id": user_id,
                "display_name": display_name,
                "action": "delete",
                "reason": reason,
                "rule_id": 0
            })
            
        except Exception as e:
            self.logger.error(f"[AI-Mod] Failed to delete message or log: {e}")
