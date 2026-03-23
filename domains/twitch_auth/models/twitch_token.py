from pydantic import BaseModel


class TwitchTokenEntity(BaseModel):
    """DB mirror of the twitch_tokens table. Do NOT use as response schema."""
    id: int
    twitch_id: str
    login: str
    display_name: str
    access_token: str
    refresh_token: str
    scopes: str          # JSON array stored as TEXT
    expires_at: str      # ISO8601
    created_at: str
    updated_at: str
