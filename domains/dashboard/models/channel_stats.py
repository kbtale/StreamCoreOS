from pydantic import BaseModel


class ChannelStatsEntity(BaseModel):
    """DB mirror of the channel_stats table."""
    id: int
    recorded_at: str
    viewer_count: int
    follower_count: int
