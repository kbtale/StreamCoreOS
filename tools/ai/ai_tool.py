import httpx
from core.base_tool import BaseTool


class AITool(BaseTool):
    """
    OpenAI-compatible AI tool.
    Config is injected via load_config() — by RestoreAIConfigPlugin on boot and
    SaveAIConfigPlugin on update. This tool never touches the DB directly.
    Supports any provider with an OpenAI-compatible /v1/chat/completions endpoint:
    OpenAI, Anthropic (compat), Gemini (compat), Ollama, LM Studio, Groq, etc.
    """

    @property
    def name(self) -> str:
        return "ai"

    async def setup(self):
        self._config: dict | None = None
        print("[AITool] Ready — waiting for config.")

    def load_config(self, config: dict) -> None:
        """Receive config from a plugin (e.g. RestoreAIConfigPlugin on boot,
        SaveAIConfigPlugin on update). AITool never touches the DB directly."""
        self._config = config

    def is_configured(self) -> bool:
        return bool(
            self._config
            and self._config.get("endpoint_url")
            and self._config.get("model")
        )

    def get_config(self) -> dict | None:
        """Returns current config without the api_key for safe exposure."""
        if not self._config:
            return None
        return {
            "provider":           self._config.get("provider", ""),
            "endpoint_url":       self._config.get("endpoint_url", ""),
            "model":              self._config.get("model", ""),
            "has_api_key":        bool(self._config.get("api_key")),
            "chat_cooldown_s":    self._config.get("chat_cooldown_s", 120),
            "chat_system_prompt": self._config.get("chat_system_prompt", ""),
            "chat_max_tokens":    self._config.get("chat_max_tokens", 200),
            "chat_temperature":   self._config.get("chat_temperature", 0.7),
            "disable_reasoning":  bool(self._config.get("disable_reasoning", False)),
            "updated_at":         self._config.get("updated_at"),
        }

    def get_chat_cooldown(self) -> int:
        """Returns the !ia command cooldown in seconds."""
        if not self._config:
            return 120
        return int(self._config.get("chat_cooldown_s") or 120)

    def get_chat_personality(self) -> dict:
        """Returns the !ia command personality settings."""
        return {
            "system_prompt": self._config.get("chat_system_prompt", "You are a helpful Twitch chat assistant. Be concise and reply in under 40 words.") if self._config else "You are a helpful Twitch chat assistant. Be concise and reply in under 40 words.",
            "max_tokens":    int(self._config.get("chat_max_tokens", 200) or 200) if self._config else 200,
            "temperature":   float(self._config.get("chat_temperature", 0.7) or 0.7) if self._config else 0.7,
        }

    async def complete(
        self,
        messages: list[dict],
        system: str | None = None,
        max_tokens: int = 300,
        temperature: float = 0.0,
    ) -> str:
        """
        Send messages to the configured LLM and return the text response.

        Args:
            messages:    List of {"role": "user"|"assistant", "content": str}
            system:      Optional system prompt (prepended automatically)
            max_tokens:  Max response tokens
            temperature: 0.0 for deterministic (moderation), higher for chat

        Returns:
            The model's text response as a string.

        Raises:
            RuntimeError: If the tool is not configured.
            httpx.HTTPStatusError: On API errors.
        """
        if not self.is_configured():
            raise RuntimeError(
                "AI tool is not configured. Set the endpoint URL, API key, and model via /ai/config."
            )

        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        payload = {
            "model":       self._config["model"],
            "messages":    all_messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }
        if self._config.get("disable_reasoning"):
            payload["reasoning"] = {"exclude": True}

        headers = {"Content-Type": "application/json"}
        api_key = self._config.get("api_key", "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        endpoint_url = self._config["endpoint_url"].rstrip("/")

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(endpoint_url, json=payload, headers=headers)
            resp.raise_for_status()
            try:
                result = resp.json()
            except Exception:
                raise RuntimeError(
                    f"Provider returned non-JSON response (status={resp.status_code}): {resp.text[:500]!r}"
                )
            choice = result["choices"][0]
            content = (choice["message"].get("content") or "").strip()
            finish_reason = choice.get("finish_reason", "")
            if not content:
                # Reasoning models (Nemotron, DeepSeek R1, etc.) put their thinking in
                # reasoning_content and the final answer in content. If content is empty
                # but reasoning_content has a clear TRUE/FALSE at the end, use it.
                reasoning = (choice["message"].get("reasoning_content") or "").strip()
                if reasoning:
                    last_word = reasoning.split()[-1].upper().rstrip(".,!?") if reasoning.split() else ""
                    if last_word in ("TRUE", "FALSE"):
                        return last_word
                raise RuntimeError(
                    f"Model returned empty content (finish_reason={finish_reason!r}). "
                    f"Raw choice: {choice}"
                )
            return content

    def get_interface_description(self) -> str:
        return """
AI Tool (ai):
    - PURPOSE: Send prompts to any OpenAI-compatible LLM. Config is stored in DB and
      managed via /ai/config endpoints. Supports OpenAI, Anthropic, Gemini, Ollama, Groq, etc.
    - CONFIG: Set via PUT /ai/config — {provider, endpoint_url, api_key, model}
    - CAPABILITIES:
        - await complete(messages, system?, max_tokens?, temperature?) -> str:
            Send a list of messages and get a text response.
            messages: [{"role": "user"|"assistant", "content": str}]
            system: optional system prompt string
            temperature: 0.0 for deterministic (ideal for moderation)
        - is_configured() -> bool: True if endpoint_url and model are set.
        - get_config() -> dict | None: Current config without the api_key.
        - load_config(config: dict): Push new config into the tool (called by plugins, never touches DB).
    - COMMON ENDPOINTS:
        OpenAI:      https://api.openai.com/v1/chat/completions
        Anthropic:   https://api.anthropic.com/v1/chat/completions
        Gemini:      https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
        Groq:        https://api.groq.com/openai/v1/chat/completions
        OpenRouter:  https://openrouter.ai/api/v1/chat/completions
        Ollama:      http://localhost:11434/v1/chat/completions
        LM Studio:   http://localhost:1234/v1/chat/completions
    """

    async def shutdown(self):
        pass
