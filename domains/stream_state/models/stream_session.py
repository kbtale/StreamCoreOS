from typing import Optional
from pydantic import BaseModel


class StreamSessionEntity(BaseModel):
    """DB mirror of the stream_sessions table. Do NOT use as response schema."""
    id: int
    twitch_stream_id: Optional[str]
    started_at: str       # ISO8601
    ended_at: Optional[str]
    title: Optional[str]
    game_name: Optional[str]
    peak_viewers: int
