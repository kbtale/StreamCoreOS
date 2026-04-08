from pydantic import BaseModel


class Viewer(BaseModel):
    id: int
    twitch_id: str
    login: str
    display_name: str
    points: int
    total_earned: int
    is_regular: bool
    first_seen: str
    last_seen: str
