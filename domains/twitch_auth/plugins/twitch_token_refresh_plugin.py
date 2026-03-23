import json
from datetime import datetime, timedelta, timezone
from core.base_plugin import BasePlugin


class TwitchTokenRefreshPlugin(BasePlugin):
    """
    Scheduled job (every 30 minutes) that proactively refreshes Twitch
    access tokens expiring within the next 60 minutes. If a token is
    refreshed successfully, it also reconnects the tool so it uses the
    new token immediately.
    """

    def __init__(self, twitch, db, scheduler, logger):
        self.twitch = twitch
        self.db = db
        self.scheduler = scheduler
        self.logger = logger

    async def on_boot(self):
        self.scheduler.add_job(
            "*/30 * * * *",
            self._refresh_expiring_tokens,
            job_id="twitch_token_refresh",
        )

    async def _refresh_expiring_tokens(self):
        try:
            tokens = await self.db.query("SELECT * FROM twitch_tokens")
            now = datetime.now(timezone.utc)
            threshold = now + timedelta(minutes=60)

            for token in tokens:
                expires_at = datetime.fromisoformat(token["expires_at"])
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)

                if expires_at > threshold:
                    continue  # still fresh, skip

                self.logger.info(f"[TwitchTokenRefresh] Refreshing token for {token['login']}")
                try:
                    new_tokens = await self.twitch.refresh_user_token(token["refresh_token"])
                    new_access = new_tokens["access_token"]
                    new_refresh = new_tokens["refresh_token"]
                    new_expires_in = new_tokens.get("expires_in", 14400)
                    new_expires_at = (
                        now + timedelta(seconds=new_expires_in)
                    ).isoformat()
                    new_scopes = new_tokens.get("scope", json.loads(token["scopes"]))

                    await self.db.execute(
                        """UPDATE twitch_tokens
                           SET access_token=$1, refresh_token=$2,
                               scopes=$3, expires_at=$4, updated_at=datetime('now')
                           WHERE twitch_id=$5""",
                        [new_access, new_refresh, json.dumps(new_scopes),
                         new_expires_at, token["twitch_id"]],
                    )

                    # Reconnect with the fresh token
                    await self.twitch.connect(
                        new_access, token["twitch_id"], token["login"]
                    )
                    self.logger.info(
                        f"[TwitchTokenRefresh] Refreshed token for {token['login']}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"[TwitchTokenRefresh] Failed to refresh token for {token['login']}: {e}"
                    )
        except Exception as e:
            self.logger.error(f"[TwitchTokenRefresh] Unexpected error: {e}")
