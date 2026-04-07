from pydantic import BaseModel
from datetime import datetime

class RedemptionLogEntity(BaseModel):
    id: int | None = None
    reward_title: str
    user_id: str
    user_name: str
    redeemed_at: datetime | None = None
